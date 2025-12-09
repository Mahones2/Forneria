from django import template

register = template.Library()


@register.filter(name='in_group')
def in_group(user, group_name):
    """Return True if the user is member of the given group name."""
    if user is None:
        return False
    if isinstance(group_name, str) is False:
        return False
    return user.groups.filter(name=group_name).exists() or user.is_superuser
