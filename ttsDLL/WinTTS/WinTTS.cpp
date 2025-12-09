#define UNICODE
#define _UNICODE

#include <windows.h>
#include <sapi.h>

extern "C"
{
    __declspec(dllexport) void SpeakText(const wchar_t* text)
    {
        // Initialize COM in STA (SAPI requires STA)
        HRESULT hr = CoInitializeEx(NULL, COINIT_APARTMENTTHREADED);
        if (FAILED(hr))
            return;

        ISpVoice* pVoice = NULL;

        // Create SAPI voice instance
        hr = CoCreateInstance(
            CLSID_SpVoice,
            NULL,
            CLSCTX_ALL,
            IID_ISpVoice,
            (void**)&pVoice
        );

        if (FAILED(hr))
        {
            CoUninitialize();
            return;
        }

        // Synchronous playback (SPF_DEFAULT instead of SPF_ASYNC)
        // → Ensures audio does NOT cut off early
        hr = pVoice->Speak(text, SPF_DEFAULT, NULL);

        if (SUCCEEDED(hr))
        {
            // Block until speech is fully finished
            pVoice->WaitUntilDone(INFINITE);
        }

        // Cleanup
        pVoice->Release();
        CoUninitialize();
    }
}
