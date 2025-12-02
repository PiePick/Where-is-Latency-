using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Networking;
using System.Text;
using System;
using System.Diagnostics;

public class GeminiTextTest : MonoBehaviour
{
    private const string URL =
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=";

    private string userText = "";

    // 응답 시간 측정용
    private Stopwatch stopwatch;

    void OnGUI()
    {
        GUI.Label(new Rect(10, 10, 300, 60), "Type your message below:");

        userText = GUI.TextField(new Rect(10, 70, 800, 100), userText, 400);

        if (GUI.Button(new Rect(10, 180, 150, 30), "Send to Gemini"))
        {
            if (string.IsNullOrEmpty(userText))
            {
                UnityEngine.Debug.LogWarning("EMPTY input!");
            }
            else
            {
                stopwatch = Stopwatch.StartNew();    // ★ 타이머 시작
                StartCoroutine(SendText(userText));
            }
        }
    }

    IEnumerator SendText(string text)
    {
        if (string.IsNullOrEmpty(AIConfig.GeminiApiKey))
        {
            UnityEngine.Debug.LogError("Gemini API KEY is missing!");
            yield break;
        }

        string json =
            "{ \"contents\": [" +
                "{ \"role\": \"user\", " +
                "\"parts\": [{ \"text\": \"" + Escape(text) + "\" }] }" +
            "] }";

        byte[] body = Encoding.UTF8.GetBytes(json);

        UnityWebRequest req = new UnityWebRequest(URL + AIConfig.GeminiApiKey, "POST");
        req.uploadHandler = new UploadHandlerRaw(body);
        req.downloadHandler = new DownloadHandlerBuffer();
        req.SetRequestHeader("Content-Type", "application/json");

        // 네트워크 요청 시점
        yield return req.SendWebRequest();

        // 타이머 종료
        stopwatch.Stop();
        double elapsedSeconds = stopwatch.Elapsed.TotalSeconds;
        double elapsedMs = stopwatch.Elapsed.TotalMilliseconds;

        if (req.result != UnityWebRequest.Result.Success)
        {
            UnityEngine.Debug.LogError("Gemini error: " + req.error);
            UnityEngine.Debug.LogError("Raw: " + req.downloadHandler.text);
            UnityEngine.Debug.Log($"⏱ Total Time: {elapsedSeconds:F4} sec  ({elapsedMs:F2} ms)");
            yield break;
        }

        UnityEngine.Debug.Log("Raw Response: " + req.downloadHandler.text);

        try
        {
            GeminiResponse parsed = JsonUtility.FromJson<GeminiResponse>(req.downloadHandler.text);
            string reply = parsed.candidates[0].content.parts[0].text;

            UnityEngine.Debug.Log("Gemini Reply: " + reply);

            // ★ 최종 응답 시간 출력
            UnityEngine.Debug.Log($"⏱ Total Time: {elapsedSeconds:F4} sec  ({elapsedMs:F2} ms)");
        }
        catch
        {
            UnityEngine.Debug.LogError("PARSE ERROR");
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