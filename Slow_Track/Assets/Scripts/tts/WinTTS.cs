using System.Runtime.InteropServices;

public static class WinTTS
{
    [DllImport("WinTTS", CallingConvention = CallingConvention.Cdecl)]
    private static extern void InitTTS();

    [DllImport("WinTTS", CallingConvention = CallingConvention.Cdecl, CharSet = CharSet.Unicode)]
    private static extern void SpeakText(string text);

    [DllImport("WinTTS", CallingConvention = CallingConvention.Cdecl)]
    private static extern void ShutdownTTS();

    private static bool initialized = false;

    public static void Initialize()
    {
        if (initialized) return;

        InitTTS();
        initialized = true;
    }

    public static void Speak(string message)
    {
        if (string.IsNullOrEmpty(message)) return;

        if (!initialized)
            Initialize();

        SpeakText(message);
    }

    public static void Shutdown()
    {
        if (!initialized) return;

        ShutdownTTS();
        initialized = false;
    }
}