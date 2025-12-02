using UnityEngine;

public class NPCController : MonoBehaviour
{
    public WhisperListener whisper;
    public GPTChat gpt;
    public GeminiChat gemini;

    private bool isProcessing;

    private int mode = 2;   // 무조건 Gemini

    void Start()
    {
        whisper.OnTextRecognized += OnWhisperText;
    }

    void OnWhisperText(string userText)
    {
        if (isProcessing) return;

        Debug.Log("[User Speech] " + userText);
        isProcessing = true;

        StartCoroutine(gemini.SendTextToGemini(userText, (reply) =>
        {
            Debug.Log("[Gemini NPC] " + reply);
            isProcessing = false;
        }));
    }
}
