"""
Unit test suite for ResolvedSchemaIntegrityGuard (v2.0 Closed-Loop Architecture)
Verifies Shannon Entropy, JSD divergence, aria-hidden exclusion, honeypot detection,
and legacy framework contracts.
"""

from behavioral_playwright.powerplay.schema_guard import ResolvedSchemaIntegrityGuard


def test_shannon_entropy_mathematical_limits():
    guard = ResolvedSchemaIntegrityGuard()
    assert guard.compute_shannon_entropy("") == 0.0
    assert guard.calculate_shannon_entropy("") == 0.0
    assert guard.compute_shannon_entropy("aaaaaaa") == 0.0
    assert abs(guard.compute_shannon_entropy("abcd" * 10) - 2.0) < 1e-4


def test_aria_hidden_does_not_trigger_false_positive():
    guard = ResolvedSchemaIntegrityGuard()
    sample_accessible_page = """
    <!DOCTYPE html>
    <html lang="en">
    <head><title>Accessible Blog Article Page</title></head>
    <body>
        <h1>Title With Accessible Icon <svg aria-hidden="true" class="icon"><path></path></svg></h1>
        <p>This is accessible web content with aria-hidden icons that screen readers safely ignore.</p>
        <button><span aria-hidden="true">★</span> Star Rating Action</button>
        <p>Additional paragraphs of clean text to ensure authentic content density and document structure.</p>
    </body>
    </html>
    """
    res = guard.audit_content_entropy(sample_accessible_page)
    assert res["decision"] == ResolvedSchemaIntegrityGuard.DECISION_NORMAL
    assert res["is_safe_to_proceed"] is True


def test_negative_coordinates_css_honeypot_caught():
    guard = ResolvedSchemaIntegrityGuard()

    # 1. Left negative
    sample_left = """
    <!DOCTYPE html>
    <html>
    <head><title>Product Page</title></head>
    <body>
        <h1>Item Title Header</h1>
        <div style="position: absolute; left: -9999px;">
            <p>Invisible honeypot text designed to trap scraper bots crawling hidden fields.</p>
        </div>
    </body>
    </html>
    """
    res_left = guard.audit_content_entropy(sample_left)
    assert res_left["decision"] == ResolvedSchemaIntegrityGuard.DECISION_HONEYPOT_ANOMALY

    # 2. Text-indent negative
    sample_indent = """
    <!DOCTYPE html>
    <html>
    <head><title>Product Page</title></head>
    <body>
        <h1>Item Title Header</h1>
        <div style="text-indent: -9999px;">
            <p>Invisible honeypot text designed to trap scraper bots crawling hidden fields.</p>
        </div>
    </body>
    </html>
    """
    res_indent = guard.audit_content_entropy(sample_indent)
    assert res_indent["decision"] == ResolvedSchemaIntegrityGuard.DECISION_HONEYPOT_ANOMALY

    # 3. Top negative
    sample_top = """
    <!DOCTYPE html>
    <html>
    <head><title>Product Page</title></head>
    <body>
        <h1>Item Title Header</h1>
        <div style="position: absolute; top: -9999px;">
            <p>Invisible honeypot text designed to trap scraper bots crawling hidden fields.</p>
        </div>
    </body>
    </html>
    """
    res_top = guard.audit_content_entropy(sample_top)
    assert res_top["decision"] == ResolvedSchemaIntegrityGuard.DECISION_HONEYPOT_ANOMALY


def test_tech_article_mentioning_datadome_not_blocked():
    guard = ResolvedSchemaIntegrityGuard()
    article_sample = """
    <!DOCTYPE html>
    <html lang="en">
    <head><title>Anti-Bot Engineering Architecture Deep Dive</title></head>
    <body>
        <h1>Understanding DataDome Defenses and Fingerprint Mitigations</h1>
        <p>DataDome inspects TLS fingerprints and device characteristics across real browser sessions. It is widely used by retailers.</p>
        <p>Engineering teams analyze DataDome headers to ensure legitimate compliance and test automation robustness across distributed infrastructure.</p>
        <p>Proper session management and realistic user-agents ensure clean communication without triggering security walls.</p>
    </body>
    </html>
    """
    res = guard.audit_content_entropy(article_sample)
    assert res["decision"] == ResolvedSchemaIntegrityGuard.DECISION_NORMAL
    assert res["is_safe_to_proceed"] is True


def test_real_challenge_wall_detected():
    guard = ResolvedSchemaIntegrityGuard()
    sample_cf_stub = """
    <html><head><script>window._cf_chl_opt={}</script></head><body><div id="cf-challenge">Verifying...</div></body></html>
    """
    res = guard.audit_content_entropy(sample_cf_stub)
    assert res["decision"] == ResolvedSchemaIntegrityGuard.DECISION_CHALLENGE_WALL
    assert res["is_safe_to_proceed"] is False


def test_baseline_variance_floor_prevents_explosion():
    guard = ResolvedSchemaIntegrityGuard()
    sample = """
    <!DOCTYPE html>
    <html>
    <head><title>Sample Blog Page Baseline</title></head>
    <body>
        <h1>Sample Title Header</h1>
        <p>Sample paragraph content for training and baseline calibration across runs.</p>
        <p>Second paragraph providing consistent text density and structural tag frequencies.</p>
    </body>
    </html>
    """
    # Train on 2 identical samples
    guard.learn_baseline([sample, sample], profile_name="test_prof")
    assert guard.baselines["test_prof"]["std_h"] >= 0.15

    # New page with slightly different text should NOT trigger honeypot anomaly
    sample_slight_diff = """
    <!DOCTYPE html>
    <html>
    <head><title>Sample Blog Page Baseline Two</title></head>
    <body>
        <h1>Sample Title Header Updated</h1>
        <p>Sample paragraph content for training and baseline calibration across runs.</p>
        <p>Second paragraph providing consistent text density and structural tag frequencies.</p>
    </body>
    </html>
    """
    res = guard.audit_content_entropy(sample_slight_diff, profile_name="test_prof")
    assert res["decision"] == ResolvedSchemaIntegrityGuard.DECISION_NORMAL


def test_legacy_framework_contracts():
    guard = ResolvedSchemaIntegrityGuard()
    assert guard.detect_content_profile('{"status": "ok"}') == "json_api"
    assert guard.detect_content_profile("<!DOCTYPE html><html><body>Normal</body></html>") == "english_html"

    # Short text bypass
    res_short = guard.audit_page_text("Short")
    assert res_short["decision"] == "PASS_BYPASS"

    # Shadow ban on repetitive text
    res_shadow = guard.audit_page_text("a" * 100)
    assert res_shadow["decision"] == "SHADOW_BAN_DETECTED"
    assert res_shadow["z_score"] < -2.5

    # Unicode bengali profile
    bengali_text = "\u0986\u09ae\u09be\u09b0 \u09b8\u09cb\u09a8\u09be\u09b0 \u09ac\u09be\u0982\u09b2\u09be " * 5
    res_bengali = guard.audit_page_text(bengali_text)
    assert res_bengali["content_profile"] == "unicode_bengali"
    assert res_bengali["decision"] == "PASS"


def test_login_form_with_csrf_hidden_inputs_not_flagged_as_honeypot():
    guard = ResolvedSchemaIntegrityGuard()
    login_form_html = """
    <!DOCTYPE html>
    <html lang="en">
    <head><title>Secure Account Login</title></head>
    <body>
        <main>
            <h1>Member Authentication</h1>
            <form action="/login" method="POST">
                <input type="hidden" name="csrf_token" value="abc123def456ghi7890">
                <input type="hidden" name="redirect_uri" value="/dashboard/billing">
                <input type="hidden" name="form_timestamp" value="1710000000">
                <label for="username">Username</label>
                <input type="text" id="username" name="username" placeholder="user@domain.com">
                <label for="password">Password</label>
                <input type="password" id="password" name="password">
                <button type="submit">Sign In to Platform</button>
            </form>
            <p>Please enter your authorized corporate credentials to proceed into the system.</p>
        </main>
    </body>
    </html>
    """
    res = guard.audit_content_entropy(login_form_html)
    assert res["decision"] == ResolvedSchemaIntegrityGuard.DECISION_NORMAL
    assert res["is_safe_to_proceed"] is True


def test_low_entropy_anomaly_detected_as_honeypot_anomaly():
    guard = ResolvedSchemaIntegrityGuard()
    # Baseline: mean_h ~ 4.65, std_h ~ 0.35
    # Create HTML with repetitive text resulting in entropy ~ 3.06 (Z = -4.53, well below -3.5, but above stub threshold 2.5)
    low_entropy_page = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <div>
        """ + ("abcdef " * 300) + """
        </div>
    </body>
    </html>
    """
    res = guard.audit_content_entropy(low_entropy_page)
    # With abs(z_score) > 3.5, this low-entropy repetitive page is caught as an anomaly, NOT passed as NORMAL
    assert res["decision"] == ResolvedSchemaIntegrityGuard.DECISION_HONEYPOT_ANOMALY
    assert res["is_safe_to_proceed"] is False
    assert res["z_score"] < -3.5


def test_baseline_variance_floor_strict_floors():
    guard = ResolvedSchemaIntegrityGuard()
    sample = """
    <!DOCTYPE html>
    <html>
    <head><title>Sample Blog Page Baseline</title></head>
    <body>
        <h1>Sample Title Header</h1>
        <p>Sample paragraph content for training and baseline calibration across runs.</p>
        <p>Second paragraph providing consistent text density and structural tag frequencies.</p>
    </body>
    </html>
    """
    guard.learn_baseline([sample, sample], profile_name="strict_prof")
    assert guard.baselines["strict_prof"]["std_h"] >= 0.20
    assert guard.baselines["strict_prof"]["mad_h"] >= 0.15
