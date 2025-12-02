using UnityEngine;
using UnityEngine.Networking;
using System;
using System.Collections;
using System.Text;

public class GPTChat : MonoBehaviour
{
    private const string URL = "https://api.openai.com/v1/chat/completions";

    // ===== NPC용 System Prompt (튜닝용) =====
    private string systemPrompt =
        "항상 차분하고 친절한 존댓말을 사용하며, 사용자와의 대화를 자연스럽게 이어간다. " +
        "한 문장 또는 한 단락 안에서 글 흐름이 매끄럽게 이어지도록 작성한다. " +
        "답변 길이는 반드시 100~400자 범위 안에서 유지한다. " +
        "음성 인식 오류가 있어 문장이 부정확해도, 대략적인 의미를 추론하여 자연스럽게 수정해 대답해라. " +
        "설명 위주가 아니라 '대화'를 이어가는 느낌을 유지하고, 불필요한 시스템 메시지나 형식적인 말투는 사용하지 않는다. " +
        "대답은 영어로 작성한다.";

    public IEnumerator AskGPT(string prompt, Action<string> callback)
    {
        if (string.IsNullOrEmpty(AIConfig.GPTApiKey))
        {
            Debug.LogError("GPT API key missing!");
            callback("ERROR");
            yield break;
        }

        // GPT 메시지 구성 (system + user)
        string json =
        "{ \"model\": \"" + AIConfig.GPTModel + "\"," +
          "\"messages\": [" +
            "{ \"role\": \"system\", \"content\": \"" + Escape(systemPrompt) + "\" }," +
            "{ \"role\": \"user\", \"content\": \"" + Escape(prompt) + "\" }" +
          "]" +
        "}";

        byte[] body = Encoding.UTF8.GetBytes(json);

        UnityWebRequest req = new UnityWebRequest(URL, "POST");
        req.uploadHandler = new UploadHandlerRaw(body);
        req.downloadHandler = new DownloadHandlerBuffer();

        req.SetRequestHeader("Content-Type", "application/json");
        req.SetRequestHeader("Authorization", "Bearer " + AIConfig.GPTApiKey);

        yield return req.SendWebRequest();

        if (req.result != UnityWebRequest.Result.Success)
        {
            Debug.LogError("GPT error: " + req.error);
            Debug.LogError("Raw: " + req.downloadHandler.text);
            callback("ERROR");
            yield break;
        }

        try
        {
            Debug.Log("[Raw GPT]: " + req.downloadHandler.text);

            GPTResponse parsed = JsonUtility.FromJson<GPTResponse>(req.downloadHandler.text);

            // ★★★ 최신 OpenAI 형식: content는 배열이며 text 필드 포함 ★★★
            string reply = parsed.choices[0].message.content[0].text;

            callback(reply);
        }
        catch (Exception e)
        {
            Debug.LogError("PARSE ERROR: " + e.Message);
            Debug.LogError("Raw JSON: " + req.downloadHandler.text);
            callback("PARSE ERROR");
        }
    }

    string Escape(string s)
    {
        return s.Replace("\\", "\\\\").Replace("\"", "\\\"");
    }

    // ===== 최신 GPT 응답 JSON 구조 =====
    [Serializable] public class GPTResponse
    {
        public Choice[] choices;
    }

    [Serializable] public class Choice
    {
        public Message message;
    }

    [Serializable] public class Message
    {
        public ContentItem[] content;   // content는 배열!
    }

    [Serializable] public class ContentItem
    {
        public string type;
        public string text;            // 여기에 실제 답변 문자열이 들어있음
    }
}
