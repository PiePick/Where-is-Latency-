using System.Collections;
using System.Collections.Generic;
using UnityEngine;

public class MicTest : MonoBehaviour
{
    private AudioClip recordedClip;
    private AudioSource audioSource;

    private string micName = null;
    private bool isRecording = false;

    void Start()
    {
        // AudioSource 자동 추가
        audioSource = gameObject.AddComponent<AudioSource>();

        // 마이크 목록 출력
        foreach (var device in Microphone.devices)
            Debug.Log("Mic found: " + device);

        if (Microphone.devices.Length == 0)
        {
            Debug.LogError("No microphone detected!");
            return;
        }

        // 첫 번째 마이크 사용
        micName = Microphone.devices[0];
        Debug.Log("Selected Mic: " + micName);
    }

    void Update()
    {
        if (Input.GetKeyDown(KeyCode.A))
        {
            StartRecording();
        }

        if (Input.GetKeyDown(KeyCode.S))
        {
            StopRecording();
        }

        if (Input.GetKeyDown(KeyCode.D))
        {
            PlayRecording();
        }
    }

    void StartRecording()
    {
        if (isRecording)
            return;

        recordedClip = Microphone.Start(micName, false, 10, 44100);
        isRecording = true;

        Debug.Log("=== Recording Started ===");
    }

    void StopRecording()
    {
        if (!isRecording)
            return;

        Microphone.End(micName);
        isRecording = false;

        Debug.Log("=== Recording Stopped ===");

        // 볼륨 확인
        if (recordedClip != null)
        {
            float[] samples = new float[recordedClip.samples];
            recordedClip.GetData(samples, 0);

            float maxAmp = 0;
            foreach (var s in samples)
                maxAmp = Mathf.Max(maxAmp, Mathf.Abs(s));

            Debug.Log("Max Amplitude = " + maxAmp);
        }
    }

    void PlayRecording()
    {
        if (recordedClip == null)
        {
            Debug.LogWarning("No audio recorded!");
            return;
        }

        audioSource.clip = recordedClip;
        audioSource.Play();

        Debug.Log("=== Playing Recorded Audio ===");
    }
}