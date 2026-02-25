using System.Collections;
using System.Collections.Generic;
using UnityEngine;

public class EmotionResetBehaviour : StateMachineBehaviour
{
    public int resetValue = 0;

    public override void OnStateExit(
        Animator animator,
        AnimatorStateInfo stateInfo,
        int layerIndex)
    {
        animator.SetInteger("EmotionID", resetValue);
    }
}
