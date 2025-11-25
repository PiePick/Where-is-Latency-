using UnityEngine;

public class MicRecorder : MonoBehaviour
{
    private bool isRecording = false;
    private string deviceName;

    void Start()
    {
        // 첫 번째 마이크 자동 선택
        if (Microphone.devices.Length > 0)
            deviceName = Microphone.devices[0];
    }

    public void StartRecording()
    {
        if (isRecording) return;

        isRecording = true;
        Microphone.End(deviceName);
        Microphone.Start(deviceName, false, 5, 44100);
    }

    public AudioClip StopRecording()
    {
        if (!isRecording) return null;

        Microphone.End(deviceName);
        isRecording = false;

        return Microphone.Start(deviceName, false, 5, 44100);
    }
}
