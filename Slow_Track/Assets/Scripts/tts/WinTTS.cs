using System.Runtime.InteropServices;

public static class WinTTS
{
    [DllImport("WinTTS", CharSet = CharSet.Unicode)]
    private static extern void SpeakText(string text);

    public static void Speak(string message)
    {
        if (string.IsNullOrEmpty(message)) return;
        SpeakText(message);
    }
    
}

