using System;
using System.Collections.Generic;
using System.Reflection;
using System.Web.Script.Serialization;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Threading;
using TavernLens.Hdt;
using Core = Hearthstone_Deck_Tracker.API.Core;

class RenderTests {
    static void Check(bool ok, string message) { if (!ok) throw new Exception(message); }
    static void Layout(Canvas canvas) {
        canvas.Measure(new Size(canvas.Width, canvas.Height));
        canvas.Arrange(new Rect(0, 0, canvas.Width, canvas.Height));
        canvas.UpdateLayout();
    }
    [STAThread] static int Main() {
        try { return Run(); }
        catch (Exception error) { Console.Error.WriteLine(error.GetType().FullName + ": " + error.Message); return 1; }
    }
    static int Run() {
        var app = new Application();
        var canvas = new Canvas { Width = 1920, Height = 1080 };
        Core.OverlayCanvas = canvas;
        var unrelated = new Border(); canvas.Children.Add(unrelated);
        var plugin = new Plugin();
        string json = "{\"version\":1,\"active\":true,\"kind\":\"hero\",\"scale\":1,\"offset\":[0,0],\"options\":[" +
            "{\"slot\":4,\"average\":\"均次 4.40\",\"details\":\"100场\",\"color\":\"#86d8ae\"}," +
            "{\"slot\":1,\"average\":\"均次 3.80\",\"details\":\"200场\",\"color\":\"#86d8ae\"}," +
            "{\"slot\":3,\"average\":\"均次 4.10\",\"details\":\"300场\",\"color\":\"#86d8ae\"}," +
            "{\"slot\":2,\"average\":\"均次 4.00\",\"details\":\"400场\",\"color\":\"#86d8ae\"}]}";
        var data = new JavaScriptSerializer().DeserializeObject(json) as Dictionary<string, object>;
        var draw = typeof(Plugin).GetMethod("Draw", BindingFlags.NonPublic | BindingFlags.Instance);
        draw.Invoke(plugin, new object[] { data, json });
        Check(canvas.Children.Count == 2, "Does not mount on the existing HDT canvas");
        var layer = (Canvas)canvas.Children[1];
        Check(!layer.IsHitTestVisible && layer.Children.Count == 4, "Layer must be click-through with four rows");
        double previous = -1;
        foreach (Border box in layer.Children) {
            Check(!box.IsHitTestVisible, "Row intercepts game input");
            double x = Canvas.GetLeft(box); Check(x > previous, "Rows are not in original slot order"); previous = x;
            Check(Canvas.GetTop(box) > 800, "Rows are not below the cards");
        }
        draw.Invoke(plugin, new object[] { data, json });
        Check(layer.Children.Count == 4, "Unchanged frame duplicates rows");
        data["active"] = false;
        draw.Invoke(plugin, new object[] { data, "hidden" });
        Check(layer.Children.Count == 0, "Ended choice stays visible");
        data["active"] = true;
        data["kind"] = "trinket";
        // Measured from the user's 1706x1279 screenshot: the card centers are
        // approximately 300,654,1009,1364; cards end at 818, buttons start at 858.
        canvas.Width = 1706; canvas.Height = 1279;
        Layout(canvas);
        draw.Invoke(plugin, new object[] { data, "trinket-4:3" });
        double[] expectedCenters = { 300, 654, 1009, 1364 };
        var baseline = new double[4];
        int index = 0;
        foreach (Border box in layer.Children) {
            double center = Canvas.GetLeft(box) + box.Width / 2;
            Check(Math.Abs(center - expectedCenters[index]) < 3, "Trinket row is not centered below its card");
            Check(Canvas.GetTop(box) > 818, "Trinket row covers card text");
            Check(Canvas.GetTop(box) + box.Height < 858, "Trinket row overlaps Hide/Confirm buttons");
            box.Child.Measure(new Size(Double.PositiveInfinity, Double.PositiveInfinity));
            Check(box.Child.DesiredSize.Height <= box.Height - box.BorderThickness.Top,
                "Compact trinket row clips the two text lines: " + box.Child.DesiredSize.Height + " / " + box.Height);
            baseline[index++] = (center - 1706.0 / 2) / 1279;
        }
        // Wide windows add space at the sides; they must not stretch the row.
        foreach (var size in new[] { new Size(1920,1080), new Size(2560,1080), new Size(1280,720), new Size(2560,1440) }) {
            canvas.Width = size.Width; canvas.Height = size.Height;
            Layout(canvas);
            // Same signature also verifies that resize invalidates positioning.
            draw.Invoke(plugin, new object[] { data, "trinket-resize" });
            index = 0;
            foreach (Border box in layer.Children) {
                double center = Canvas.GetLeft(box) + box.Width / 2;
                Check(Math.Abs((center - size.Width / 2) / size.Height - baseline[index++]) < .0001,
                    "Trinket spacing changes with screen aspect ratio");
                Check(Canvas.GetLeft(box) >= 0 && Canvas.GetLeft(box) + box.Width <= size.Width,
                    "Trinket row is outside the client area");
            }
        }
        data["offset"] = new object[] { .02, -.03 };
        draw.Invoke(plugin, new object[] { data, "trinket-offset" });
        var moved = (Border)layer.Children[0];
        Check(Math.Abs(Canvas.GetTop(moved) - 1440 * (.642 - .03)) < .01, "Manual offset is not applied");
        Check(layer.Children.Count == 4 && !layer.IsHitTestVisible, "Trinket rows intercept input or duplicate");
        plugin.OnUnload();
        var frame = new DispatcherFrame();
        app.Dispatcher.BeginInvoke(DispatcherPriority.Background, new Action(delegate { frame.Continue = false; }));
        Dispatcher.PushFrame(frame);
        Check(canvas.Children.Count == 1 && canvas.Children[0] == unrelated, "Unload damaged other HDT UI");
        Console.WriteLine("HDT adapter: mounted canvas, hero slots, screenshot-calibrated trinkets, 4:3/16:9/21:9, resize, offsets, click-through, hide, unload PASS");
        app.Shutdown(); return 0;
    }
}
