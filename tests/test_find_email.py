from src import find_email


def test_registrable_domain_strips_www_and_subdomains():
    assert find_email.registrable_domain("www.hinestrucking.com") == "hinestrucking.com"
    assert find_email.registrable_domain("careers.hinestrucking.com") == "hinestrucking.com"
    assert find_email.registrable_domain("hinestrucking.com") == "hinestrucking.com"


def test_base_url_from_job_url_on_company_domain():
    lead = {"job_url": "https://www.hinestrucking.com/careers/controller"}
    assert find_email.base_url_for_lead(lead) == "https://www.hinestrucking.com"


def test_base_url_none_for_job_boards():
    for url in [
        "https://remoteok.com/remote-jobs/12345",
        "https://www.indeed.com/viewjob?jk=abc",
        "https://www.ziprecruiter.com/jobs/xyz",
    ]:
        assert find_email.base_url_for_lead({"job_url": url}) is None


def test_base_url_prefers_explicit_website():
    lead = {"website": "hinestrucking.com", "job_url": "https://indeed.com/x"}
    assert find_email.base_url_for_lead(lead) == "https://hinestrucking.com"


def test_candidate_urls_include_contact_pages():
    urls = find_email.candidate_urls("https://acme.com")
    assert "https://acme.com/" in urls
    assert "https://acme.com/contact" in urls
    assert "https://acme.com/careers" in urls
    assert len(urls) == len(set(urls))  # de-duplicated


def test_extract_emails_from_mailto_and_text():
    html = """
      <a href="mailto:Careers@Hinestrucking.com?subject=hi">Apply</a>
      <p>General questions: info@hinestrucking.com.</p>
      <img src="logo@2x.png">
    """
    emails = find_email.extract_emails(html)
    assert "careers@hinestrucking.com" in emails   # lowercased, query stripped
    assert "info@hinestrucking.com" in emails
    assert not any(e.endswith(".png") for e in emails)


def test_best_email_prefers_same_domain_role_address():
    emails = [
        "someguy@gmail.com",
        "info@hinestrucking.com",
        "careers@hinestrucking.com",
    ]
    assert find_email.best_email(emails, "hinestrucking.com") == "careers@hinestrucking.com"


def test_best_email_skips_noreply_and_examples():
    emails = ["noreply@hinestrucking.com", "test@example.com"]
    assert find_email.best_email(emails, "hinestrucking.com") is None


def test_best_email_none_when_empty():
    assert find_email.best_email([], "hinestrucking.com") is None
