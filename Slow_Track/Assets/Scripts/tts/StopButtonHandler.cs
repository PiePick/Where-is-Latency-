using UnityEngine;
using UnityEngine.UI;

public class StopButtonHandler : MonoBehaviour
{
    public SpeechRecognizer recognizer;

    private void Start()
    {
        
    }

    private void Update()
    {
        if ( Input.GetKeyUp( KeyCode.Space ) )
        {
            recognizer.SpeakFinalResult();
        }
    }
}
