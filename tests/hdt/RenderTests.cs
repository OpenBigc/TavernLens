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
    [STAThread] static int Main() {
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
        plugin.OnUnload();
        var frame = new DispatcherFrame();
        app.Dispatcher.BeginInvoke(DispatcherPriority.Background, new Action(delegate { frame.Continue = false; }));
        Dispatcher.PushFrame(frame);
        Check(canvas.Children.Count == 1 && canvas.Children[0] == unrelated, "Unload damaged other HDT UI");
        Console.WriteLine("HDT adapter: mounted canvas, 4 click-through strips, correct slots, hide, unload PASS");
        app.Shutdown(); return 0;
    }
}
