from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from ..forms import EndNodeForm
from accounts.models import Person


@login_required
def addEndNode(request):
    if request.method == 'POST':
        end_node_form = EndNodeForm(request.POST)
        if end_node_form.is_valid():
            end_node_form.save()
            messages.success(request, 'Your device was successfully added!')
        else:
            messages.error(request, ('Error saving device', end_node_form.errors))
        return redirect('addEndNode')
    end_node_form = EndNodeForm()
    username = request.user
    person = Person.objects.get(username=username)
    end_node_form.fields["surveyor_org"].queryset = person.orgs()
    return render(request, 'device/addEndNode.html', {'form': end_node_form})
