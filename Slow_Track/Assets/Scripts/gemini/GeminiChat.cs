using UnityEngine;
using UnityEngine.Networking;
using System;
using System.Collections;
using System.Text;

public class GeminiChat : MonoBehaviour
{
    // 기본 URL
    private const string BASE_URL =
        "https://generativelanguage.googleapis.com/v1beta/models/";

    // ===== NPC 튜닝 프롬프트 =====
    private string systemPrompt =
        "모든 대답은 반드시 100~400자 범위 안에서 자연스럽고 매끄럽게 작성한다. " +
        "감정이 과하지 않은 친절하고 차분한 존댓말을 사용한다. " +
        "설명보다 대화를 이어가는 느낌으로 반응하며, 과도하게 길거나 장황한 문장 구성은 피한다. " +
        "음성 인식 오류로 문장 구조가 이상하거나 단어가 누락되었어도, 대략적인 의미를 파악해 자연스럽게 응답한다. " +
        "항상 하나의 대답만 제공하고, 불필요한 말머리나 시스템적인 문구는 포함하지 않는다."+
        "대답은 영어로 작성한다.";

    // ===== 텍스트를 Gemini로 보내서 답변 받기 =====
    public IEnumerator SendTextToGemini(string text, Action<string> callback)
    {
        if (string.IsNullOrEmpty(AIConfig.GeminiApiKey))
        {
            Debug.LogError("Gemini API Key missing in AIConfig.GeminiApiKey");
            callback?.Invoke("ERROR: NO API KEY");
            yield break;
        }

        if (string.IsNullOrEmpty(AIConfig.GeminiModel))
        {
            Debug.LogWarning("Gemini model empty → default gemini-2.5-flash 사용");
            AIConfig.GeminiModel = "gemini-2.5-flash";
        }

        // Gemini JSON 포맷 (system prompt + user prompt)
        string json =
            "{ \"contents\": [" +
                "{ \"role\": \"user\", \"parts\": [{ \"text\": \"" + Escape(systemPrompt) + "\" }] }," +
                "{ \"role\": \"user\", \"parts\": [{ \"text\": \"" + Escape(text) + "\" }] }" +
            "] }";

        byte[] body = Encoding.UTF8.GetBytes(json);

        string url = BASE_URL + AIConfig.GeminiModel + ":generateContent?key=" + AIConfig.GeminiApiKey;

        UnityWebRequest req = new UnityWebRequest(url, "POST");
        req.uploadHandler = new UploadHandlerRaw(body);
        req.downloadHandler = new DownloadHandlerBuffer();
        req.SetRequestHeader("Content-Type", "application/json");

        yield return req.SendWebRequest();

        if (req.result != UnityWebRequest.Result.Success)
        {
            Debug.LogError("Gemini error: " + req.error);
            Debug.LogError("Raw: " + req.downloadHandler.text);
            callback?.Invoke("ERROR");
            yield break;
        }

        string res = req.downloadHandler.text;
        Debug.Log("Gemini Raw Response: " + res);

        try
        {
            GeminiResponse parsed = JsonUtility.FromJson<GeminiResponse>(res);
            string reply = parsed.candidates[0].content.parts[0].text;
            callback?.Invoke(reply);
        }
        catch (Exception e)
        {
            Debug.LogError("Gemini parse error: " + e.Message);
            callback?.Invoke("PARSE ERROR");
        }
    }

    string Escape(string s)
    {
        return s.Replace("\\", "\\\\").Replace("\"", "\\\"");
    }

    [Serializable] public class GeminiResponse { public Candidate[] candidates; }
    [Serializable] public class Candidate { public Content content; }
    [Serializable] public class Content { public Part[] parts; }
    [Serializable] public class Part { public string text; }
}
