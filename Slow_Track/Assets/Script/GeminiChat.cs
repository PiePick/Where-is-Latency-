using UnityEngine;
using UnityEngine.Networking;
using System;
using System.Collections;
using System.Text;

public class GeminiChat : MonoBehaviour
{
    private const string URL =
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=";

    public IEnumerator SendAudioToGemini(byte[] wavData, Action<string> callback)
    {
        if (string.IsNullOrEmpty(AIConfig.GeminiKey))
        {
            Debug.LogError("Gemini API Key missing!");
            callback("ERROR");
            yield break;
        }

        string base64 = Convert.ToBase64String(wavData);

        string json =
        "{ \"contents\": [{" +
            "\"role\": \"user\"," +
            "\"parts\": [" +
                "{ \"text\": \"Transcribe this audio and respond naturally.\" }," +
                "{ \"inlineData\": { " +
                    "\"mimeType\": \"audio/wav\", " +
                    "\"data\": \"" + base64 + "\" " +
                "} }" +
            "]" +
        "}] }";

        byte[] body = Encoding.UTF8.GetBytes(json);

        UnityWebRequest req = new UnityWebRequest(URL + AIConfig.GeminiKey, "POST");
        req.uploadHandler = new UploadHandlerRaw(body);
        req.downloadHandler = new DownloadHandlerBuffer();
        req.SetRequestHeader("Content-Type", "application/json");

        yield return req.SendWebRequest();

        if (req.result != UnityWebRequest.Result.Success)
        {
            Debug.LogError("Gemini error: " + req.error);
            Debug.LogError("Raw Response: " + req.downloadHandler.text);
            callback("ERROR");
            yield break;
        }

        string res = req.downloadHandler.text;
        Debug.Log("Raw Gemini Response: " + res);

        try
        {
            GeminiResponse parsed = JsonUtility.FromJson<GeminiResponse>(res);
            string text = parsed.candidates[0].content.parts[0].text;
            callback(text);
        }
        catch
        {
            callback("PARSE ERROR");
        }
    }

    [Serializable] public class GeminiResponse { public Candidate[] candidates; }
    [Serializable] public class Candidate { public Content content; }
    [Serializable] public class Content { public Part[] parts; }
    [Serializable] public class Part { public string text; }
}
