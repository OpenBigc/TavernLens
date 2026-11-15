using System;
using System.Collections;
using System.Collections.Generic;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Net;
using System.Text;
using System.Threading.Tasks;
using System.Web.Script.Serialization;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Threading;
using Hearthstone_Deck_Tracker.Plugins;
using HdtCore = Hearthstone_Deck_Tracker.API.Core;

namespace TavernLens.Hdt
{
    public sealed class Plugin : IPlugin
    {
        public string Name { get { return "TavernLens · 酒馆透镜"; } }
        public string Description { get { return "英雄与饰品大数据"; } }
        public string ButtonText { get { return "设置"; } }
        public string Author { get { return "OpenBigc"; } }
        public Version Version { get { return new Version(0, 1, 4); } }
        public MenuItem MenuItem { get { return null; } }
        private bool enabled, busy, startAttempted;
        private int generation;
        private DispatcherTimer timer;
        private Canvas layer, host;
        private Window settings;
        private string error = "数据服务未连接";
        private string lastFrame;
        private double lastWidth, lastHeight;
        private static readonly string Folder = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "TavernLens");
        private static readonly JavaScriptSerializer Json = new JavaScriptSerializer();

        public void OnLoad()
        {
            enabled = true;
            int current = ++generation;
            Application.Current.Dispatcher.BeginInvoke(new Action(delegate {
                if (!enabled || generation != current) return;
                timer = new DispatcherTimer { Interval = TimeSpan.FromMilliseconds(250) };
                timer.Tick += async delegate { await Poll(); };
                timer.Start();
            }));
        }

        public void OnUnload()
        {
            enabled = false;
            generation++;
            Application.Current.Dispatcher.BeginInvoke(new Action(delegate {
                if (timer != null) timer.Stop();
                if (host != null && layer != null) host.Children.Remove(layer);
                host = null; layer = null; lastFrame = null;
                if (settings != null) settings.Close();
            }));
        }

        public void OnUpdate() { }

        public void OnButtonPress()
        {
            Application.Current.Dispatcher.BeginInvoke(new Action(OpenSettings));
        }

        private async Task Poll()
        {
            if (!enabled || busy) return;
            busy = true;
            int current = generation;
            try
            {
                string text = await Task.Run(delegate {
                    var request = (HttpWebRequest)WebRequest.Create("http://127.0.0.1:27183/state");
                    request.Timeout = 1200;
                    request.ReadWriteTimeout = 1200;
                    request.Proxy = null;
                    using (var response = request.GetResponse())
                    using (var reader = new StreamReader(response.GetResponseStream(), Encoding.UTF8))
                        return reader.ReadToEnd();
                });
                if (!enabled || generation != current) return;
                var frame = Json.DeserializeObject(text) as Dictionary<string, object>;
                if (frame == null || Number(frame, "version", 0) != 1) throw new InvalidDataException();
                error = "";
                Draw(frame, text);
            }
            catch (Exception exception)
            {
                if (!enabled || generation != current) return;
                error = "数据服务未连接";
                Hide();
                Log(exception);
                if (!startAttempted) StartBackend();
            }
            finally { busy = false; }
        }

        private void StartBackend()
        {
            startAttempted = true;
            string path = Path.Combine(Path.GetDirectoryName(typeof(Plugin).Assembly.Location), "TavernLensBackend.exe");
            if (!File.Exists(path)) return;
            try {
                Process.Start(new ProcessStartInfo(path, "--idle-timeout 60") {
                    UseShellExecute = false, CreateNoWindow = true,
                    WorkingDirectory = Path.GetDirectoryName(path)
                });
            } catch (Exception exception) { Log(exception); }
        }

        private void Hide()
        {
            if (layer != null) layer.Children.Clear();
            lastFrame = null;
        }

        private void Draw(Dictionary<string, object> frame, string signature)
        {
            if (!Boolean(frame, "active")) { Hide(); return; }
            string kind = Text(frame, "kind");
            if (kind != "hero" && kind != "trinket") { Hide(); return; }
            object raw;
            if (!frame.TryGetValue("options", out raw) || !(raw is IEnumerable)) { Hide(); return; }
            var options = ((IEnumerable)raw).Cast<object>().Select(x => x as Dictionary<string, object>).ToList();
            if (options.Count < 2 || options.Count > 4 || options.Any(x => x == null)) { Hide(); return; }
            var slots = options.Select(x => (int)Number(x, "slot", 0)).ToList();
            if (slots.Distinct().Count() != options.Count || slots.Any(x => x < 1 || x > options.Count)) { Hide(); return; }
            Canvas canvas = HdtCore.OverlayCanvas;
            if (canvas == null) { Hide(); return; }
            if (canvas != host) {
                if (host != null && layer != null) host.Children.Remove(layer);
                host = canvas;
                layer = new Canvas { IsHitTestVisible = false };
                Panel.SetZIndex(layer, 10000);
                host.Children.Add(layer);
                lastFrame = null;
            }
            double width = host.ActualWidth > 0 ? host.ActualWidth : host.Width;
            double height = host.ActualHeight > 0 ? host.ActualHeight : host.Height;
            if (Double.IsNaN(width) || Double.IsNaN(height) || width < 1 || height < 1) { Hide(); return; }
            if (lastFrame == signature && width == lastWidth && height == lastHeight) return;
            layer.Children.Clear();
            lastFrame = signature; lastWidth = width; lastHeight = height;
            bool trinket = kind == "trinket";
            // Trinket choices use the centered 4:3 board, including in wide
            // windows. Their spacing scales with board height, not screen width.
            double aspect = trinket ? 4.0 / 3 : 16.0 / 9;
            double sw = Math.Min(width, height * aspect), sh = sw / aspect;
            double sx = (width - sw) / 2, sy = (height - sh) / 2;
            double factor = Math.Max(.65, Math.Min(2.5, sh / 1080)) * Math.Max(.6, Math.Min(2, Number(frame, "scale", 1)));
            double ox = 0, oy = 0;
            if (frame.TryGetValue("offset", out raw) && raw is object[]) {
                var offsets = (object[])raw;
                if (offsets.Length == 2) { ox = Clamp(Convert.ToDouble(offsets[0]), -.5, .5); oy = Clamp(Convert.ToDouble(offsets[1]), -.5, .5); }
            }
            double[] xs = Centers(kind, options.Count);
            foreach (var option in options.OrderBy(x => Number(x, "slot", 0))) {
                int slot = (int)Number(option, "slot", 1);
                var panel = new StackPanel { HorizontalAlignment = HorizontalAlignment.Center, VerticalAlignment = VerticalAlignment.Center };
                Brush color = Brushes.WhiteSmoke;
                try { color = (Brush)new BrushConverter().ConvertFromString(Text(option, "color")); } catch { }
                panel.Children.Add(new TextBlock { Text = Text(option, "average"), Foreground = color,
                    FontFamily = new FontFamily("Microsoft YaHei UI"), FontSize = (trinket ? 14 : 16) * factor,
                    FontWeight = FontWeights.SemiBold, TextAlignment = TextAlignment.Center });
                panel.Children.Add(new TextBlock { Text = Text(option, "details"), Foreground = new SolidColorBrush(Color.FromRgb(162, 168, 179)),
                    FontFamily = new FontFamily("Microsoft YaHei UI"), FontSize = (trinket ? 9 : 11) * factor, TextAlignment = TextAlignment.Center });
                double bw = 210 * factor, bh = (trinket ? 31 : 54) * factor;
                var box = new Border { Width = bw, Height = bh, Child = panel, IsHitTestVisible = false,
                    Background = new SolidColorBrush(Color.FromArgb(230, 20, 24, 30)), BorderThickness = new Thickness(0, trinket ? factor : 1, 0, 0),
                    BorderBrush = new SolidColorBrush(Color.FromRgb(53, 62, 73)) };
                Canvas.SetLeft(box, Clamp(sx + sw * (xs[slot - 1] + ox) - bw / 2, 0, width - bw));
                Canvas.SetTop(box, Clamp(sy + sh * ((trinket ? .642 : .795) + oy), 0, height - bh));
                layer.Children.Add(box);
            }
        }

        public static double[] Centers(string kind, int count)
        {
            if (kind == "hero") {
                if (count == 2) return new[] { .422, .586 };
                if (count == 3) return new[] { .340, .504, .669 };
                return new[] { .257, .422, .586, .751 };
            }
            // Calibrated to the four card centers in the 4:3 trinket dialog.
            // A shared midpoint also keeps two/three-option dialogs centered.
            return Enumerable.Range(0, count).Select(i => .4875 + (i - (count - 1) / 2.0) * (5.0 / 24)).ToArray();
        }

        private static double Clamp(double value, double low, double high) { return Math.Max(low, Math.Min(high, value)); }
        private static string Text(Dictionary<string, object> data, string key) { object x; return data.TryGetValue(key, out x) && x != null ? x.ToString() : ""; }
        private static bool Boolean(Dictionary<string, object> data, string key) { object x; return data.TryGetValue(key, out x) && x is bool && (bool)x; }
        private static double Number(Dictionary<string, object> data, string key, double fallback) {
            double x; return Double.TryParse(Text(data, key), NumberStyles.Float, CultureInfo.InvariantCulture, out x) && !Double.IsNaN(x) && !Double.IsInfinity(x) ? x : fallback;
        }

        private static void Log(Exception exception)
        {
            // Poll failures are expected while the backend starts. Avoid a
            // repeated traceback on every 250ms connection attempt.
            Debug.WriteLine("TavernLens: " + exception.Message);
        }

        private void OpenSettings()
        {
            if (settings != null) { settings.Activate(); return; }
            Dictionary<string, object> config;
            string path = Path.Combine(Folder, "settings.json");
            try { config = Json.DeserializeObject(File.ReadAllText(path)) as Dictionary<string, object>; }
            catch { config = null; }
            config = config ?? new Dictionary<string, object>();
            settings = new Window { Title = Name, Width = 390, Height = 540, ResizeMode = ResizeMode.NoResize,
                WindowStartupLocation = WindowStartupLocation.CenterScreen, Background = new SolidColorBrush(Color.FromRgb(20, 24, 30)),
                Foreground = Brushes.WhiteSmoke, FontFamily = new FontFamily("Microsoft YaHei UI"), FontSize = 13 };
            var box = new StackPanel { Margin = new Thickness(22) };
            settings.Content = box;
            box.Children.Add(new TextBlock { Text = String.IsNullOrEmpty(error) ? "数据服务已连接" : error, Margin = new Thickness(0, 0, 0, 12) });
            var rank = Choice(box, "分段", new[] { "全分段", "前50%", "前25%", "前10%", "前1%" }, new[] { "100", "50", "25", "10", "1" }, Text(config, "mmr"), "100");
            var period = Choice(box, "时间", new[] { "当前补丁", "近7天", "近3天", "全部时间" }, new[] { "last-patch", "past-seven", "past-three", "all-time" }, Text(config, "period"), "last-patch");
            var mode = Choice(box, "模式", new[] { "单人", "双人" }, new[] { "solo", "duo" }, Text(config, "mode"), "solo");
            var scale = Field(box, "评分条大小", Number(config, "scale", 1).ToString(CultureInfo.InvariantCulture));
            var offsetFields = new List<TextBox>();
            object offsetObject;
            var offsetMap = config.TryGetValue("offsets", out offsetObject) ? offsetObject as Dictionary<string, object> : null;
            foreach (string kind in new[] { "hero", "trinket" }) {
                object valueObject;
                var values = offsetMap != null && offsetMap.TryGetValue(kind, out valueObject) ? valueObject as object[] : null;
                for (int axis = 0; axis < 2; axis++) {
                    double position = values != null && values.Length == 2 ? Convert.ToDouble(values[axis]) * 100 : 0;
                    offsetFields.Add(Field(box, (kind == "hero" ? "英雄" : "饰品") + (axis == 0 ? "横移 %" : "纵移 %"), position.ToString(CultureInfo.InvariantCulture)));
                }
            }
            var failure = new TextBlock { Foreground = Brushes.IndianRed, Margin = new Thickness(0, 8, 0, 8) };
            box.Children.Add(failure);
            var save = new Button { Content = "保存", Padding = new Thickness(16, 5, 16, 5), HorizontalAlignment = HorizontalAlignment.Right };
            box.Children.Add(save);
            save.Click += delegate {
                double value;
                if (!Double.TryParse(scale.Text, NumberStyles.Float, CultureInfo.InvariantCulture, out value) || !(value >= .6 && value <= 2)) { failure.Text = "大小范围为 0.6～2"; return; }
                var offsets = new double[4];
                for (int i = 0; i < 4; i++) {
                    if (!Double.TryParse(offsetFields[i].Text, NumberStyles.Float, CultureInfo.InvariantCulture, out offsets[i]) || !(offsets[i] >= -50 && offsets[i] <= 50)) { failure.Text = "位置范围为 -50～50"; return; }
                    offsets[i] /= 100;
                }
                config["mmr"] = ((ComboBoxItem)rank.SelectedItem).Tag;
                config["period"] = ((ComboBoxItem)period.SelectedItem).Tag;
                config["mode"] = ((ComboBoxItem)mode.SelectedItem).Tag;
                config["scale"] = value;
                config["offsets"] = new Dictionary<string, object> { { "hero", new[] { offsets[0], offsets[1] } }, { "trinket", new[] { offsets[2], offsets[3] } } };
                try {
                    Directory.CreateDirectory(Folder);
                    string temporary = path + ".hdt.tmp";
                    File.WriteAllText(temporary, Json.Serialize(config), new UTF8Encoding(false));
                    if (File.Exists(path)) File.Replace(temporary, path, null); else File.Move(temporary, path);
                    settings.Close();
                } catch (Exception exception) { failure.Text = "设置保存失败"; Log(exception); }
            };
            settings.Closed += delegate { settings = null; };
            settings.Show();
        }

        private static ComboBox Choice(Panel parent, string title, string[] labels, string[] values, string current, string fallback)
        {
            var row = new DockPanel { Margin = new Thickness(0, 5, 0, 5) };
            row.Children.Add(new TextBlock { Text = title, Width = 110, VerticalAlignment = VerticalAlignment.Center });
            var combo = new ComboBox();
            for (int i = 0; i < values.Length; i++) combo.Items.Add(new ComboBoxItem { Content = labels[i], Tag = values[i] });
            combo.SelectedIndex = Math.Max(0, Array.IndexOf(values, String.IsNullOrEmpty(current) ? fallback : current));
            row.Children.Add(combo); parent.Children.Add(row); return combo;
        }

        private static TextBox Field(Panel parent, string title, string value)
        {
            var row = new DockPanel { Margin = new Thickness(0, 5, 0, 5) };
            row.Children.Add(new TextBlock { Text = title, Width = 110 });
            var field = new TextBox { Text = value };
            row.Children.Add(field); parent.Children.Add(row); return field;
        }
    }
}
