using UnityEngine;
using System.Collections;

public class NPCController : MonoBehaviour
{
    public MicRecorder recorder;
    public VoskSTT vosk;
    public GPTChat gpt;
    public GeminiChat gemini;   

    private AudioClip recorded;
    private bool isProcessing = false;

    // 1 = GPT 모드, 2 = Gemini 모드
    private int mode = 1;

    void Update()
    {
        // === 모드 전환 ===
        if (Input.GetKeyDown(KeyCode.Alpha1))
        {
            mode = 1;
            Debug.Log("[NPC] Mode switched → GPT");
        }

        if (Input.GetKeyDown(KeyCode.Alpha2))
        {
            mode = 2;
            Debug.Log("[NPC] Mode switched → Gemini");
        }

        // === 음성 녹음 ===
        if (isProcessing) return;

        if (Input.GetKeyDown(KeyCode.R))
        {
            recorder.StartRecording();
            Debug.Log("[NPC] Recording... (Press T to stop)");
        }

        if (Input.GetKeyDown(KeyCode.T))
        {
            recorded = recorder.StopRecording();
            Debug.Log("[NPC] Recording stopped.");

            if (recorded == null)
            {
                Debug.LogError("Audio Clip is null!");
                return;
            }

            isProcessing = true;

            // === Vosk로 음성을 텍스트로 변환 ===
            string recognized = vosk.GetTextFromAudioClip(recorded);
            Debug.Log("[Answer] " + recognized);

            // === GPT 모드 ===
            if (mode == 1)
            {
                StartCoroutine(gpt.AskGPT(recognized, (reply) =>
                {
                    Debug.Log("[GPT NPC] " + reply);
                    isProcessing = false;
                }));
            }

            // === Gemini 모드 ===
            else if (mode == 2)
            {
                byte[] wavBytes = WavUtility.AudioClipToWav(recorded);

                StartCoroutine(gemini.SendTextToGemini(recognized, (reply) =>
                {
                    Debug.Log("[Gemini NPC] " + reply);
                    isProcessing = false;
                }));
            }
        }
    }
}
