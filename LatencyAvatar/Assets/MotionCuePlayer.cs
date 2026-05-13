using System.Collections;
using UnityEngine;

public class MotionCuePlayer : MonoBehaviour
{
    [SerializeField] private Animator animator;

    [Header("Motion Cue State Names")]
    [SerializeField] private string neutralState = "neutral_base";
    [SerializeField] private string sadState = "sad_sigh_intro";
    [SerializeField] private string smileState = "smile_nod_intro";
    [SerializeField] private string surprisedState = "surprised_gasp_intro";
    [SerializeField] private string angryState = "angry_intro";

    [Header("Timing")]
    [SerializeField] private float fadeTime = 0.25f;
    [SerializeField] private float returnDelay = 1.4f;

    private Coroutine returnCoroutine;

    private void Reset()
    {
        animator = GetComponent<Animator>();
    }

    private void Update()
    {
        if (Input.GetKeyDown(KeyCode.Alpha1))
        {
            PlayMotionCue(neutralState, false);
        }

        if (Input.GetKeyDown(KeyCode.Alpha2))
        {
            PlayMotionCue(sadState, true);
        }

        if (Input.GetKeyDown(KeyCode.Alpha3))
        {
            PlayMotionCue(smileState, true);
        }

        if (Input.GetKeyDown(KeyCode.Alpha4))
        {
            PlayMotionCue(surprisedState, true);
        }

        if (Input.GetKeyDown(KeyCode.Alpha5))
        {
            PlayMotionCue(angryState, true);
        }
    }

    public void PlayMotionCue(string motionCue, bool returnToNeutral)
    {
        if (animator == null)
        {
            Debug.LogWarning("Animator가 연결되지 않았습니다.");
            return;
        }

        animator.CrossFadeInFixedTime(motionCue, fadeTime, 0, 0f);
        Debug.Log($"Motion Cue Played: {motionCue}");

        if (returnCoroutine != null)
        {
            StopCoroutine(returnCoroutine);
        }

        if (returnToNeutral)
        {
            returnCoroutine = StartCoroutine(ReturnToNeutralAfterDelay());
        }
    }

    private IEnumerator ReturnToNeutralAfterDelay()
    {
        yield return new WaitForSeconds(returnDelay);
        animator.CrossFadeInFixedTime(neutralState, fadeTime, 0, 0f);
        Debug.Log("Returned to neutral_base");
    }
}