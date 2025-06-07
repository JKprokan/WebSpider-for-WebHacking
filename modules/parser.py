from bs4 import BeautifulSoup

def extract_inputs_with_form_context(html: str, target_attrs: set) -> list:
    soup = BeautifulSoup(html, "html.parser")
    results = []

    form_input_ids = set()
    for form in soup.find_all("form"):
        method = form.get("method", "").upper()
        action = form.get("action", "")
        for tag in form.find_all(["input", "textarea", "select"]):
            input_info = {
                attr: value
                for attr, value in tag.attrs.items()
                if attr in target_attrs or attr.startswith("aria-")
            }
            if input_info:
                input_info["form_method"] = method
                input_info["form_action"] = action
                results.append(input_info)
            form_input_ids.add(id(tag))

    for tag in soup.find_all(["input", "textarea", "select"]):
        if id(tag) not in form_input_ids:
            input_info = {
                attr: value
                for attr, value in tag.attrs.items()
                if attr in target_attrs or attr.startswith("aria-")
            }
            if input_info:
                results.append(input_info)

    return results
