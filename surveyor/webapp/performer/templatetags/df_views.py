from django import template

register = template.Library()


@register.filter
def frame_delivery_percent(hits, misses):
    # success_rate = hits / (hits + misses)
    return hits / (hits + misses) * 100
