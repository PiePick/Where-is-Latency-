using UnityEngine;
using System;
using Vosk;

public class VoskSTT : MonoBehaviour
{
    private Model model;
    private VoskRecognizer recognizer;

    void Start()
    {
        Vosk.Vosk.SetLogLevel(0);

        string modelPath = System.IO.Path.Combine(
            Application.streamingAssetsPath,
            "vosk-model-small-en-us-0.15"
        );

        Debug.Log("Loading Vosk model from: " + modelPath);

        model = new Model(modelPath);
        recognizer = new VoskRecognizer(model, 16000.0f);

        Debug.Log("Vosk model loaded!");
    }

    // 기존 함수
    public string Recognize(AudioClip clip)
    {
        if (clip == null)
            return "";

        return ProcessClip(clip);
    }

    // NPCController에서 사용하는 이름
    public string GetTextFromAudioClip(AudioClip clip)
    {
        if (clip == null)
            return "";

        return ProcessClip(clip);
    }

    // 실제 처리 로직 (중복 방지)
    private string ProcessClip(AudioClip clip)
    {
        float[] samples = new float[clip.samples];
        clip.GetData(samples, 0);

        short[] shorts = new short[samples.Length];
        for (int i = 0; i < samples.Length; i++)
            shorts[i] = (short)(samples[i] * 32767);

        recognizer.AcceptWaveform(shorts, shorts.Length * 2);
        string json = recognizer.FinalResult();

        VoskResult result = JsonUtility.FromJson<VoskResult>(json);
        return result.text;
    }

    [Serializable]
    public class VoskResult { public string text; }
}
