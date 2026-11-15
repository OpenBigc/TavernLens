// A minimal, independently implemented test host for the documented HDT API.
// It is not shipped and contains no HDT implementation code.
using System;
using System.Windows.Controls;
namespace Hearthstone_Deck_Tracker.Plugins {
    public interface IPlugin {
        string Name { get; } string Description { get; } string ButtonText { get; }
        string Author { get; } Version Version { get; } MenuItem MenuItem { get; }
        void OnLoad(); void OnUnload(); void OnButtonPress(); void OnUpdate();
    }
}
namespace Hearthstone_Deck_Tracker.API {
    public static class Core { public static Canvas OverlayCanvas { get; set; } }
}
