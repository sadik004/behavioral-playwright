# Behavioral Humanizer & Biomechanical Models

> **Last Verified Against Commit**: `68a3d1e`
> **Status**: [VERIFIED]

---

## 1. Biomechanical Interaction Models

The humanization engine eliminates anti-bot detection by mathematically emulating human motor control:

### I. Log-Normal Keystroke Cadence
Human typing is non-uniform. Keystroke hold times and character transition delays follow a log-normal probability density function:

$$f(t) = \frac{1}{t \sigma \sqrt{2\pi}} \exp\left( -\frac{(\ln t - \mu)^2}{2\sigma^2} \right)$$

In [`BrowserNamespace._get_keystroke_hold_delay`](file:///c:/Users/User/SAA/bp_facade12.py#L400), each keypress duration is sampled randomly between 40ms and 120ms with natural variation.

### II. Bezier Newtonian Mouse Curves
Rather than linear point-to-point mouse jumps, mouse movements calculate 500-point cubic Bézier trajectories influenced by virtual gravity, inertia, and micro-tremor jitter.

### III. Saccade Stepped Scrolling
Human eye tracking (saccadic movement) during reading causes stepped scrolling with variable micro-pauses (50ms–150ms) rather than continuous automated scrolling.
