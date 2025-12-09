using UnityEngine;
using UnityEngine.Android;
using UnityEngine.Events;
using SpeechRecognitionSystem;

public class AudioRecorder : MonoBehaviour, IAudioProvider {
    public int MicrophoneIndex = 0;
    public int GetRecordPosition( ) {
        return Microphone.GetPosition( _deviceName );
    }
    public AudioClip GetAudioClip( ) {
        return _audioClip;
    }
    public bool IsRecording( ) {
        return Microphone.IsRecording( _deviceName );
    }

    public int MicrophoneSampleRate = 16000;

    public bool StartOnAwake = true;

    public float Frequency {
        get {
            return MicrophoneSampleRate;
        }
    }

    public float[ ] GetData( ) {
        if (IsRecording()) {
            int pos = Microphone.GetPosition( _deviceName );
            int diff = pos - _lastSample;
            if ( diff > 0 ) {
                var samples = new float[ diff ];
                _audioClip.GetData( samples, _lastSample );
                _lastSample = pos;
                return samples;
            }
            _lastSample = pos;
        }
        return null;
    }

    public AudioReadyEvent MicReady = new AudioReadyEvent( );

    private void Awake( ) {
        if ( Application.platform == RuntimePlatform.Android ) {
            if ( !Permission.HasUserAuthorizedPermission( Permission.Microphone ) ) {
                Permission.RequestUserPermission( Permission.Microphone );
            }
        }
    }

    private void Update( ) {
        bool micAutorized = true;
        if ( Application.platform == RuntimePlatform.Android ) {
            micAutorized = Permission.HasUserAuthorizedPermission( Permission.Microphone );
        }
        if ( micAutorized ) {
            if ( _firstLoad ) {
                if (StartOnAwake)
                    OnStart( );

                this.MicReady?.Invoke( this );
                _firstLoad = false;
            }
        }
    }
    private void OnDestroy( ) {
        OnStop( );
        _firstLoad = true;
    }

    public void OnStart( ) {
        _deviceName = Microphone.devices[ MicrophoneIndex ];
        _audioClip = Microphone.Start( _deviceName, true, LENGTH_SEC, MicrophoneSampleRate );
        this.MicReady?.Invoke( this );
    }

    public void OnStop( ) {
        Microphone.End( _deviceName );
    }

    private bool _firstLoad = true;
    private AudioClip _audioClip = null;
    private const int LENGTH_SEC = 2;
    private string _deviceName;

    private int _lastSample = 0;
}
