from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag(takes_context=True)
def query_transform(context, **kwargs):
    request = context["request"]
    updated = request.GET.copy()
    for key, value in kwargs.items():
        if value:
            updated[key] = value
        elif key in updated:
            del updated[key]
    return updated.urlencode()


@register.simple_tag(takes_context=True)
def sort_header(context, prefix, field, label):
    request = context["request"]
    current_sort = request.GET.get(f"{prefix}_sort", "")
    current_order = request.GET.get(f"{prefix}_order", "asc")

    updated = request.GET.copy()

    if current_sort == field:
        if current_order == "asc":
            updated[f"{prefix}_sort"] = field
            updated[f"{prefix}_order"] = "desc"
            arrow = ' <span class="sort-arrow">&#9650;</span>'
        else:
            if f"{prefix}_sort" in updated:
                del updated[f"{prefix}_sort"]
            if f"{prefix}_order" in updated:
                del updated[f"{prefix}_order"]
            arrow = ' <span class="sort-arrow">&#9660;</span>'
    else:
        updated[f"{prefix}_sort"] = field
        updated[f"{prefix}_order"] = "asc"
        arrow = ""

    sorted_class = " sorted" if current_sort == field else ""
    qs = updated.urlencode()
    html = (
        f'<th class="sortable{sorted_class}">'
        f'<a href="?{qs}">{label}{arrow}</a>'
        f"</th>"
    )
    return mark_safe(html)
