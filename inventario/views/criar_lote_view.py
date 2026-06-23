from django.shortcuts import render, redirect
from ..models import LoteBipagem
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden

@login_required(login_url='inventario:login')
def criar_lote_view(request):
    if request.method == 'POST' and request.user.groups.filter(name='INV_PA_VISUALIZADOR_MASTER').exists():
        return HttpResponseForbidden("Você não tem permissão para criar lotes.")

    if request.method == 'POST':
        grupo = request.user.groups.first()
        if grupo:
            nome_grupo = grupo.name
            if nome_grupo.startswith("INV_PA_"):
                nome_exibicao = nome_grupo.replace("INV_PA_", "", 1)
            else:
                nome_exibicao = nome_grupo

            total_lotes_grupo = LoteBipagem.objects.filter(group_user=grupo).count()

            lote = LoteBipagem.objects.create(
                user_created=request.user,
                group_user=grupo,
                group_user_txt=nome_exibicao,
                numero_lote=total_lotes_grupo + 1
            )

            return redirect('inventario:lote', lote.id)

    return render(request, 'inventario/criar_lote.html')
