using UnityEngine;
using System.IO;
using System;

public class WhisperListener : MonoBehaviour
{
    public string whisperTextFilePath = @"C:\Users\max47\Desktop\whisper_output.txt";

    private string lastText = "";
    public Action<string> OnTextRecognized;

    private float timer = 0f;

    void Update()
    {
        timer += Time.deltaTime;

        // 0.5초마다 파일 확인
        if (timer < 0.5f) return;
        timer = 0f;

        if (!File.Exists(whisperTextFilePath))
            return;

        string current = File.ReadAllText(whisperTextFilePath).Trim();

        if (!string.IsNullOrEmpty(current) && current != lastText)
        {
            lastText = current;
            Debug.Log("[Whisper] " + current);

            OnTextRecognized?.Invoke(current);
        }
    }
}
