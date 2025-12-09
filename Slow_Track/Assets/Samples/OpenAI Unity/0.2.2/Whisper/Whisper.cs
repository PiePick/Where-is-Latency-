using OpenAI;
using UnityEngine;
using UnityEngine.UI;

namespace Samples.Whisper
{
    public class Whisper : MonoBehaviour
    {
        [SerializeField] private Button recordButton;   // 녹음 시작
        [SerializeField] private Button stopButton;     // 녹음 종료
        [SerializeField] private Image progressBar;
        [SerializeField] private Text message;
        [SerializeField] private Dropdown dropdown;

        private readonly string fileName = "output.wav";

        private AudioClip clip;
        private bool isRecording = false;
        private float time = 0f;

        private string currentMic = null;   // 현재 사용 중인 마이크 이름

        private float transcriptionStartTime;

        private OpenAIApi openai = new OpenAIApi("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"); // 키만 채워 넣으면 됨

        private void Start()
        {
            WinTTS.Speak("Sunday morning rain is falling Steal some covers, share some skin. Clouds are shrouding us in moments unforgettable You twist to fit the mold that I am in");

#if UNITY_WEBGL && !UNITY_EDITOR
            dropdown.options.Add(new Dropdown.OptionData("Microphone not supported on WebGL"));
#else
            foreach (var device in Microphone.devices)
            {
                dropdown.options.Add(new Dropdown.OptionData(device));
            }

            recordButton.onClick.AddListener(StartRecording);
            stopButton.onClick.AddListener(StopRecording);
            dropdown.onValueChanged.AddListener(ChangeMicrophone);

            var index = PlayerPrefs.GetInt("user-mic-device-index", 0);
            dropdown.SetValueWithoutNotify(index);

            stopButton.interactable = false;
#endif
        }

        private void ChangeMicrophone(int index)
        {
            PlayerPrefs.SetInt("user-mic-device-index", index);
        }

        private void StartRecording()
        {
            isRecording = true;
            time = 0f;

            recordButton.interactable = false;
            stopButton.interactable = true;

#if !UNITY_WEBGL
            var index = PlayerPrefs.GetInt("user-mic-device-index", 0);
            currentMic = dropdown.options[index].text;

            // 최대 30초 버퍼, 16kHz (Whisper에 적당, 용량도 작음)
            clip = Microphone.Start(currentMic, false, 30, 16000);
            Debug.Log("Recording started on mic: " + currentMic);
#endif
        }

        private async void StopRecording()
        {
            if (!isRecording) return;
            isRecording = false;
            transcriptionStartTime = Time.realtimeSinceStartup;
            Debug.Log("Transcription started at: " + transcriptionStartTime);
            stopButton.interactable = false;
            recordButton.interactable = true;

#if !UNITY_WEBGL
            if (clip == null || string.IsNullOrEmpty(currentMic))
            {
                message.text = "No audio clip or mic.";
                Debug.LogError("StopRecording: clip or currentMic is null.");
                return;
            }

            // 녹음 종료 전에 현재 위치(샘플 수) 가져오기
            int samples = Microphone.GetPosition(currentMic);
            Microphone.End(currentMic);
            Debug.Log("Recorded samples: " + samples);

            if (samples <= 0)
            {
                message.text = "No audio detected.";
                Debug.LogError("Audio error: no samples recorded.");
                return;
            }

            // 실제 녹음된 길이만큼 데이터 가져오기
            int channels = clip.channels;
            float[] rawData = new float[samples * channels];
            clip.GetData(rawData, 0);

            AudioClip trimmedClip = AudioClip.Create(
                "trimmed",
                samples,
                channels,
                clip.frequency,
                false
            );
            trimmedClip.SetData(rawData, 0);

            // WAV 변환
            byte[] wavData = SaveWav.Save(fileName, trimmedClip);
            Debug.Log("WAV size (bytes): " + wavData.Length);
#else
            byte[] wavData = null;
#endif

            message.text = "Transcripting...";

            var req = new CreateAudioTranscriptionsRequest
            {
                FileData = new FileData
                {
                    Data = wavData,
                    Name = "audio.wav"
                },
                Model = "whisper-1"
                // Language = "ko" 같이 고정하고 싶으면 여기 넣어도 됨
            };

            try
            {
                var res = await openai.CreateAudioTranscription(req);

                progressBar.fillAmount = 0;

                message.text = res.Text;
                Debug.Log("Whisper Result: " + res.Text);
                

                // 총 소요 시간 계산
                float endTime = Time.realtimeSinceStartup;
                float duration = endTime - transcriptionStartTime;

                Debug.Log("Transcription completed at: " + endTime);
                Debug.Log("Total transcription time: " + duration + " sec");

                WinTTS.Speak(res.Text);
            }
            catch (System.Exception e)
            {
                message.text = "Error: " + e.Message;
                Debug.LogError("Whisper Error: " + e);
            }
        }

        private void Update()
        {
            if (isRecording)
            {
                time += Time.deltaTime;
                // 단순하게 1초마다 한 바퀴 도는 형태
                progressBar.fillAmount = time % 1f;
            }
        }
    }
}
