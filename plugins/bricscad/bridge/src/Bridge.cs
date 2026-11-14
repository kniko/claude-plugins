// ClaudeBridge: runs inside BricsCAD and answers the bricscad MCP server over a named pipe.
//
// Protocol: one request per connection on \\.\pipe\claude-bricscad, a single UTF-8 JSON line each way.
//   {"op":"ping"}                               -> state of BricsCAD (active doc, quiescent, active command)
//   {"op":"lisp","expr":"(+ 1 2)","timeout":60} -> evaluates LISP in the active document, returns its value
//   {"op":"selection"}                          -> current pickfirst selection + the last non-empty one
//
// All BricsCAD API calls run on the main thread (marshalled through a hidden WinForms control).
// The pipe thread owns the timeout, so a modal dialog or a command waiting for input can never hang
// the MCP server: it gets {"ok":false,"status":"busy",...} instead.
using System;
using System.Collections.Generic;
using System.IO;
using System.IO.Pipes;
using System.Security.AccessControl;
using System.Security.Principal;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;
using System.Threading;
using System.Threading.Tasks;
using System.Windows.Forms;
using Bricscad.ApplicationServices;
using Bricscad.EditorInput;
using Teigha.DatabaseServices;
using Teigha.Runtime;
using App = Bricscad.ApplicationServices.Application;

[assembly: ExtensionApplication(typeof(ClaudeBridge.Bridge))]
[assembly: CommandClass(typeof(ClaudeBridge.Commands))]

namespace ClaudeBridge
{
    public class Bridge : IExtensionApplication
    {
#if TESTBUILD
        // side-by-side test copy: pipe named after the assembly, e.g. claude-bricscad-ClaudeBridgeT3
        public static readonly string PipeName = "claude-bricscad-" + typeof(Bridge).Assembly.GetName().Name;
#else
        public const string PipeName = "claude-bricscad";
#endif
        static readonly string LogFile = Path.Combine(Path.GetTempPath(), PipeName + ".log");

        internal static void Log(string s)
        {
            try { File.AppendAllText(LogFile, DateTime.Now.ToString("s") + " " + s + Environment.NewLine); } catch { }
        }
        const string ResultSym = "*claude-r*";
        const string Pending = "\u0002pending";
        const string ErrTag = "\u0001ERR ";

        static Control ui;                     // created on the main thread; BeginInvoke = run there
        static Thread pipeThread;
        static volatile bool stopping;
        static JsonArray lastSelection = new JsonArray();
        static string lastSelectionDoc = "";
        static DateTime lastSelectionTime;
        static readonly HashSet<Document> hooked = new HashSet<Document>();

        public void Initialize()
        {
            ui = new Control();
            var _ = ui.Handle;                 // force the window handle now (CreateControl skips hidden controls)
            Log("Initialize on thread " + Environment.CurrentManagedThreadId);
            foreach (Document d in App.DocumentManager) Hook(d);
            App.DocumentManager.DocumentCreated += (s, e) => Hook(e.Document);
            pipeThread = new Thread(PipeLoop) { IsBackground = true, Name = "ClaudeBridge pipe" };
            pipeThread.Start();
            Write("\nClaudeBridge loaded: pipe \\\\.\\pipe\\" + PipeName + "\n");
        }

        public void Terminate() { stopping = true; }

        static void Write(string s)
        {
            try { App.DocumentManager.MdiActiveDocument?.Editor.WriteMessage(s); } catch { }
        }

        static void Hook(Document d)
        {
            if (d == null || !hooked.Add(d)) return;
            d.ImpliedSelectionChanged += (s, e) =>
            {
                try
                {
                    var sel = ReadSelection(d);
                    if (sel.Count > 0) { lastSelection = sel; lastSelectionDoc = d.Name; lastSelectionTime = DateTime.Now; }
                }
                catch { }
            };
        }

        // ---------------------------------------------------------------- pipe
        static void PipeLoop()
        {
            var sec = new PipeSecurity();
            sec.AddAccessRule(new PipeAccessRule(WindowsIdentity.GetCurrent().User,
                PipeAccessRights.FullControl, AccessControlType.Allow));
            // Several instances, and the next one is created as soon as a client connects, so the pipe name
            // never disappears between requests. Requests themselves are served one at a time (gate).
            while (!stopping)
            {
                NamedPipeServerStream pipe = null;
                try
                {
                    pipe = NamedPipeServerStreamAcl.Create(PipeName, PipeDirection.InOut,
                        NamedPipeServerStream.MaxAllowedServerInstances,
                        PipeTransmissionMode.Byte, PipeOptions.Asynchronous, 0, 0, sec);
                    pipe.WaitForConnection();
                    var p = pipe;
                    Task.Run(() => Serve(p));
                }
                catch (System.Exception ex)
                {
                    pipe?.Dispose();
                    if (stopping) return;
                    Log("pipe: " + ex);
                    Thread.Sleep(200);
                }
            }
        }

        static readonly SemaphoreSlim gate = new SemaphoreSlim(1, 1);
        static readonly JsonSerializerOptions JsonOpts = new JsonSerializerOptions
        {
            Encoder = System.Text.Encodings.Web.JavaScriptEncoder.UnsafeRelaxedJsonEscaping,
            // BricsCAD's host has no default resolver: without this, ToJsonString throws
            TypeInfoResolver = new System.Text.Json.Serialization.Metadata.DefaultJsonTypeInfoResolver(),
        };

        static void Serve(NamedPipeServerStream pipe)
        {
            using (pipe)
            {
                try
                {
                    var reader = new StreamReader(pipe, new UTF8Encoding(false), false, 4096, true);
                    string line = reader.ReadLine();
                    string reply;
                    if (!gate.Wait(TimeSpan.FromSeconds(5)))
                        reply = "{\"ok\":false,\"status\":\"busy\",\"error\":\"another request is running\"}";
                    else
                        try { reply = Handle(line); } finally { gate.Release(); }
                    var bytes = new UTF8Encoding(false).GetBytes(reply + "\n");
                    pipe.Write(bytes, 0, bytes.Length);
                    pipe.Flush();
                    pipe.WaitForPipeDrain();
                }
                catch (System.Exception ex) { Log("serve: " + ex); }
            }
        }

        static string Handle(string line)
        {
            JsonObject res;
            try
            {
                var req = JsonNode.Parse(line ?? "{}").AsObject();
                string op = (string)req["op"] ?? "ping";
                int timeout = req["timeout"] != null ? (int)req["timeout"] : 60;
                res = op switch
                {
                    "ping" => OnMain(State, 10),
                    "selection" => OnMain(Selection, 10),
                    "lisp" => Lisp((string)req["expr"] ?? "nil", timeout),
                    "send" => OnMain(() => Send((string)req["text"] ?? ""), 10),
                    "cancel" => Cancel(),
                    _ => Err("unknown op " + op),
                };
            }
            catch (System.Exception ex) { Log("handle: " + ex); res = Err(ex.Message); }
            try { return res.ToJsonString(JsonOpts); }
            catch (System.Exception ex)
            {
                Log("serialize: " + ex);
                return "{\"ok\":false,\"error\":" + JsonSerializer.Serialize(ex.Message, JsonOpts) + "}";
            }
        }

        static JsonObject Err(string msg) => new JsonObject { ["ok"] = false, ["error"] = msg };

        static JsonObject Busy(string why)
        {
            var o = new JsonObject { ["ok"] = false, ["status"] = "busy", ["error"] = why };
            try { o["state"] = ui.InvokeRequired ? OnMain(State, 3) : State(); } catch { }   // never wait on ourselves
            return o;
        }

        // Run f on the main thread; the calling (pipe) thread waits at most `seconds`.
        static JsonObject OnMain(Func<JsonObject> f, int seconds)
        {
            var tcs = new TaskCompletionSource<JsonObject>(TaskCreationOptions.RunContinuationsAsynchronously);
            ui.BeginInvoke(new Action(() =>
            {
                try { tcs.TrySetResult(f()); } catch (System.Exception ex) { tcs.TrySetResult(Err(ex.Message)); }
            }));
            if (tcs.Task.Wait(TimeSpan.FromSeconds(seconds))) return tcs.Task.Result;
            return new JsonObject { ["ok"] = false, ["status"] = "busy", ["error"] = "main thread did not respond in " + seconds + " s (modal dialog open?)" };
        }

        // ---------------------------------------------------------------- ops
        static JsonObject State()
        {
            var doc = App.DocumentManager.MdiActiveDocument;
            var o = new JsonObject { ["ok"] = true, ["bridge"] = typeof(Bridge).Assembly.GetName().Version.ToString(3) };
            o["active"] = doc?.Name;
            o["quiescent"] = doc != null && doc.Editor.IsQuiescent;
            o["cmdnames"] = Convert.ToString(App.GetSystemVariable("CMDNAMES"));
            o["cmdactive"] = Convert.ToInt32(App.GetSystemVariable("CMDACTIVE"));
            var docs = new JsonArray();
            foreach (Document d in App.DocumentManager) docs.Add((JsonNode)d.Name);
            o["documents"] = docs;
            return o;
        }

        // Queue a command line in the active document and return at once (never blocks like COM SendCommand).
        static JsonObject Send(string text)
        {
            var doc = App.DocumentManager.MdiActiveDocument;
            if (doc == null) return Err("no active document");
            if (!doc.Editor.IsQuiescent || Convert.ToInt32(App.GetSystemVariable("CMDACTIVE")) != 0)
                return Busy("BricsCAD is busy: command '" + Convert.ToString(App.GetSystemVariable("CMDNAMES")) + "' is active");
            doc.SendStringToExecute(text, true, false, true);
            return new JsonObject { ["ok"] = true, ["status"] = "sent" };
        }

        [System.Runtime.InteropServices.DllImport("user32.dll")]
        static extern bool PostMessage(IntPtr hWnd, uint msg, IntPtr wParam, IntPtr lParam);

        // Press Esc twice in BricsCAD: cancels a running command or a LISP waiting for input. Works while the
        // main thread is inside a command (the posted keys are processed by its input loop).
        static JsonObject Cancel()
        {
            var h = System.Diagnostics.Process.GetCurrentProcess().MainWindowHandle;
            for (int i = 0; i < 2; i++) PostMessage(h, 0x0102 /* WM_CHAR */, (IntPtr)27, IntPtr.Zero);
            Thread.Sleep(500);
            var st = OnMain(State, 5);
            st["status"] = "cancel sent";
            return st;
        }

        static JsonObject Selection()
        {
            var doc = App.DocumentManager.MdiActiveDocument;
            var o = new JsonObject { ["ok"] = true };
            o["current"] = doc != null ? ReadSelection(doc) : new JsonArray();
            o["last"] = JsonNode.Parse(lastSelection.ToJsonString(JsonOpts));
            o["last_document"] = lastSelectionDoc;
            o["last_time"] = lastSelectionTime == default ? null : lastSelectionTime.ToString("s");
            return o;
        }

        static JsonArray ReadSelection(Document doc)
        {
            var arr = new JsonArray();
            var r = doc.Editor.SelectImplied();
            if (r.Status != PromptStatus.OK || r.Value == null) return arr;
            using (var tr = doc.Database.TransactionManager.StartTransaction())
            {
                foreach (ObjectId id in r.Value.GetObjectIds())
                {
                    var e = new JsonObject { ["handle"] = id.Handle.ToString(), ["type"] = id.ObjectClass.DxfName };
                    if (tr.GetObject(id, OpenMode.ForRead) is Entity ent)
                    {
                        e["layer"] = ent.Layer;
                        try
                        {
                            var x = ent.GeometricExtents;
                            e["bbox"] = new JsonArray(
                                new JsonArray(Math.Round(x.MinPoint.X, 4), Math.Round(x.MinPoint.Y, 4), Math.Round(x.MinPoint.Z, 4)),
                                new JsonArray(Math.Round(x.MaxPoint.X, 4), Math.Round(x.MaxPoint.Y, 4), Math.Round(x.MaxPoint.Z, 4)));
                        }
                        catch { }
                    }
                    arr.Add(e);
                }
                tr.Commit();
            }
            return arr;
        }

        // LISP: wrap the expression so its value (or error) lands in *claude-r* as a string, send it to the
        // active document's command line, and wait for LispEnded. Long or multi-line code goes via a temp file.
        static JsonObject Lisp(string expr, int timeout)
        {
            var done = new TaskCompletionSource<JsonObject>(TaskCreationOptions.RunContinuationsAsynchronously);
            var cancelled = false;
            var start = OnMain(() =>
            {
                var doc = App.DocumentManager.MdiActiveDocument;
                if (doc == null) return Err("no active document");
                if (!doc.Editor.IsQuiescent || Convert.ToInt32(App.GetSystemVariable("CMDACTIVE")) != 0)
                    return Busy("BricsCAD is busy: command '" + Convert.ToString(App.GetSystemVariable("CMDNAMES")) + "' is active");

                string wrapped =
                    "(progn (setq " + ResultSym + " (vl-catch-all-apply (function (lambda () " + expr + "\n))))" +
                    " (setq " + ResultSym + " (if (vl-catch-all-error-p " + ResultSym + ") (strcat \"" + ErrTag + "\" (vl-catch-all-error-message " + ResultSym + "))" +
                    " (vl-prin1-to-string " + ResultSym + "))) (princ))";
                string send;
                if (wrapped.Length > 1500 || expr.Contains('\n') || expr.Contains('\r'))
                {
                    string f = Path.Combine(Path.GetTempPath(), "claude_bridge_req.lsp");
                    File.WriteAllText(f, wrapped, new UTF8Encoding(true));
                    send = "(load \"" + f.Replace('\\', '/') + "\") ";
                }
                else send = wrapped.Replace('\n', ' ') + " ";

                object filedia = App.GetSystemVariable("FILEDIA"), cmddia = App.GetSystemVariable("CMDDIA");
                App.SetSystemVariable("FILEDIA", 0);
                App.SetSystemVariable("CMDDIA", 0);
                Bricscad.Global.Editor.SetLispSymbol(ResultSym,
                    new ResultBuffer(new TypedValue(5005 /* RTSTR */, Pending)));

                EventHandler finish = null;
                finish = (s, e) =>
                {
                    object v = null;
                    try { v = Bricscad.Global.Editor.GetLispSymbol(ResultSym); } catch { }
                    if (v is ResultBuffer rb)
                    {
                        var vals = rb.AsArray();
                        v = vals.Length > 0 ? vals[0].Value : null;
                    }
                    string sv = v as string;
                    if (sv == Pending) return;                       // an inner LISP ended, not ours
                    doc.LispEnded -= finish;
                    try { App.SetSystemVariable("FILEDIA", filedia); App.SetSystemVariable("CMDDIA", cmddia); } catch { }
                    if (cancelled) return;
                    if (sv != null && sv.StartsWith(ErrTag))
                        done.TrySetResult(new JsonObject { ["ok"] = false, ["error"] = sv.Substring(ErrTag.Length) });
                    else
                        done.TrySetResult(new JsonObject { ["ok"] = true, ["result"] = sv ?? Convert.ToString(v) });
                };
                doc.LispEnded += finish;
                doc.SendStringToExecute(send, true, false, false);
                return new JsonObject { ["ok"] = true, ["status"] = "sent" };
            }, 10);
            if ((bool?)start["ok"] != true || (string)start["status"] != "sent") return start;
            if (done.Task.Wait(TimeSpan.FromSeconds(timeout))) return done.Task.Result;
            cancelled = true;
            return Busy("LISP did not finish in " + timeout + " s (waiting for input or a dialog?)");
        }
    }

    public class Commands
    {
#if !TESTBUILD
        [CommandMethod("CLAUDEBRIDGE")]   // test copies register no command (names would clash)
#endif
        public void Status()
        {
            App.DocumentManager.MdiActiveDocument?.Editor.WriteMessage(
                "\nClaudeBridge running on \\\\.\\pipe\\" + Bridge.PipeName + "\n");
        }
    }
}
