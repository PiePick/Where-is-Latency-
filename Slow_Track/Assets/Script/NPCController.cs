using UnityEngine;
using System.Collections;

public class NPCController : MonoBehaviour
{
    public MicRecorder recorder;
    public GeminiChat gemini;

    private AudioClip recorded;
    private bool isProcessing = false;

    void Update()
    {
        if (isProcessing) return;

        if (Input.GetKeyDown(KeyCode.R))
        {
            recorder.StartRecording();
            Debug.Log("Recording... Press T to stop.");
        }

        if (Input.GetKeyDown(KeyCode.T))
        {
            recorded = recorder.StopRecording();
            if (recorded == null)
            {
                Debug.LogError("Recorded clip NULL");
                return;
            }

            byte[] wav = WavUtility.AudioClipToWav(recorded);
            isProcessing = true;

            StartCoroutine(gemini.SendAudioToGemini(wav, (text) =>
            {
                Debug.Log("=== GEMINI RESULT ===");
                Debug.Log(text);
                Debug.Log("====================");

                isProcessing = false;
            }));
        }
    }
}
