using System.Collections;
using UnityEngine;
using UnityEngine.Networking;
using System.Text;
using System;

public class GPTTextTest : MonoBehaviour
{
    private string userText = "";

    void OnGUI()
    {
        GUI.Label(new Rect(10, 10, 300, 25), "Type your message below:");
        userText = GUI.TextField(new Rect(10, 40, 400, 25), userText, 200);

        if (GUI.Button(new Rect(10, 80, 150, 30), "Send to GPT"))
        {
            StartCoroutine(SendText(userText));
        }
    }

    IEnumerator SendText(string text)
    {
        if (string.IsNullOrEmpty(AIConfig.GPTApiKey))
        {
            Debug.LogError("GPT API KEY missing!");
            yield break;
        }

        string json =
            "{ \"model\": \"" + AIConfig.GPTModel + "\"," +
            "\"messages\": [{ \"role\": \"user\", \"content\": \"" + text + "\" }] }";

        byte[] body = Encoding.UTF8.GetBytes(json);

        UnityWebRequest req = new UnityWebRequest("https://api.openai.com/v1/chat/completions", "POST");
        req.uploadHandler = new UploadHandlerRaw(body);
        req.downloadHandler = new DownloadHandlerBuffer();

        req.SetRequestHeader("Content-Type", "application/json");
        req.SetRequestHeader("Authorization", "Bearer " + AIConfig.GPTApiKey);

        yield return req.SendWebRequest();

        if (req.result != UnityWebRequest.Result.Success)
        {
            Debug.LogError("GPT error: " + req.error);
            Debug.LogError("Raw: " + req.downloadHandler.text);
            yield break;
        }

        Debug.Log("Raw: " + req.downloadHandler.text);

        try
        {
            GPTResponse parsed = JsonUtility.FromJson<GPTResponse>(req.downloadHandler.text);
            Debug.Log("GPT Reply: " + parsed.choices[0].message.content);
        }
        catch
        {
            Debug.LogError("PARSE ERROR");
        }
    }

    [Serializable] public class GPTResponse { public Choice[] choices; }
    [Serializable] public class Choice { public Message message; }
    [Serializable] public class Message { public string role; public string content; }
}
