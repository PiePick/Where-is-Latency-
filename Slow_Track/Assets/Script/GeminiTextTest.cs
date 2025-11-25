using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Networking;
using System.Text;
using System;

public class GeminiTextTest : MonoBehaviour
{
    private const string URL =
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=";

    private string userText = "";

    void OnGUI()
    {
        GUI.Label(new Rect(10, 10, 300, 25), "Type your message below:");

        userText = GUI.TextField(new Rect(10, 40, 400, 25), userText, 200);

        if (GUI.Button(new Rect(10, 80, 150, 30), "Send to Gemini"))
        {
            if (string.IsNullOrEmpty(userText))
                Debug.LogWarning("EMPTY input!");
            else
                StartCoroutine(SendText(userText));
        }
    }

    IEnumerator SendText(string text)
    {
        if (string.IsNullOrEmpty(AIConfig.GeminiKey))
        {
            Debug.LogError("Gemini API KEY is missing!");
            yield break;
        }

        string json =
            "{ \"contents\": [" +
                "{ \"role\": \"user\", " +
                "\"parts\": [{ \"text\": \"" + Escape(text) + "\" }] }" +
            "] }";

        byte[] body = Encoding.UTF8.GetBytes(json);

        UnityWebRequest req = new UnityWebRequest(URL + AIConfig.GeminiKey, "POST");
        req.uploadHandler = new UploadHandlerRaw(body);
        req.downloadHandler = new DownloadHandlerBuffer();
        req.SetRequestHeader("Content-Type", "application/json");

        yield return req.SendWebRequest();

        if (req.result != UnityWebRequest.Result.Success)
        {
            Debug.LogError("Gemini error: " + req.error);
            Debug.LogError("Raw: " + req.downloadHandler.text);
            yield break;
        }

        Debug.Log("Raw Response: " + req.downloadHandler.text);

        try
        {
            GeminiResponse parsed = JsonUtility.FromJson<GeminiResponse>(req.downloadHandler.text);
            Debug.Log("Gemini Reply: " + parsed.candidates[0].content.parts[0].text);
        }
        catch
        {
            Debug.LogError("PARSE ERROR");
        }
    }

    string Escape(string s)
    {
        return s.Replace("\"", "\\\"");
    }

    [Serializable] public class GeminiResponse { public Candidate[] candidates; }
    [Serializable] public class Candidate { public Content content; }
    [Serializable] public class Content { public Part[] parts; }
    [Serializable] public class Part { public string text; }
}