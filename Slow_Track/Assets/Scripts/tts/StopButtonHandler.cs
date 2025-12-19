using UnityEngine;
using UnityEngine.UI;

public class StopButtonHandler : MonoBehaviour
{
    public SpeechRecognizer recognizer;

    private void Start()
    {
        GetComponent<Button>().onClick.AddListener(OnStopClicked);
    }

    private void OnStopClicked()
    {
        recognizer.SpeakFinalResult();
    }
}
