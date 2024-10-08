from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from epi_shops.models import Epis, Carrinhos
from .forms import EpiForm, AddToCartForm
from django.db.models import Q  # Para buscas com filtros
from django.contrib.auth.mixins import LoginRequiredMixin  # Para exigir login em CBVs
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect

@login_required
def index(request):
    """
    View para a página inicial, exibindo a lista de EPIs,
    carrinho de compras e valor total.
    """
    search_query = request.GET.get('search')
    if search_query:
        epis = Epis.objects.filter(
            Q(nome__icontains=search_query) | Q(descricao__icontains=search_query)
        )
    else:
        epis = Epis.objects.all()

    paginator = Paginator(epis, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Carrinho de compras
    carrinho_itens = Carrinhos.objects.filter(usuario=request.user)
    valor_total = sum(item.epi.valor * item.quantidade for item in carrinho_itens)

    # Formulário para adicionar ao carrinho
    add_to_cart_form = AddToCartForm()


    context = {
        'epis': page_obj,
        'page_obj': page_obj,
        'is_paginated': page_obj.has_other_pages(),
        'carrinho_itens': carrinho_itens,
        'valor_total': valor_total,
        'add_to_cart_form': add_to_cart_form, # Formulário para o carrinho
    }
    return render(request, 'epi_shops/index.html', context)

class EpiList(LoginRequiredMixin, ListView):
    """
    View para listar todos os EPIs, com paginação e busca.
    """
    model = Epis
    template_name = 'epi_shops/epi_list.html'
    context_object_name = 'epis'
    paginate_by = 10  # 10 EPIs por página

    def get_context_data(self, **kwargs):
        """
        Adiciona o formulário de adicionar ao carrinho ao contexto.
        """
        context = super().get_context_data(**kwargs)
        context['add_to_cart_form'] = AddToCartForm()
        return context

    def get_queryset(self):
        """
        Filtra os EPIs com base na busca (nome ou descrição).
        """
        queryset = super().get_queryset()
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(nome__icontains=search_query) | Q(descricao__icontains=search_query)
            )
        return queryset


class EpiDetail(LoginRequiredMixin, DetailView):
    """
    View para exibir os detalhes de um EPI específico.
    """
    model = Epis
    template_name = 'epi_shops/epi_detail.html'
    context_object_name = 'epi'

    def get_context_data(self, **kwargs):
        """
        Adiciona o formulário de adicionar ao carrinho ao contexto,
        pré-preenchido com o EPI atual.
        """
        context = super().get_context_data(**kwargs)
        context['add_to_cart_form'] = AddToCartForm(initial={'epi': self.object})  # Inicializa o formulário com o EPI atual
        return context


class EpiCreate(LoginRequiredMixin, CreateView):
    """
    View para criar um novo EPI.
    """
    model = Epis
    form_class = EpiForm
    template_name = 'epi_shops/epi_form.html'
    success_url = reverse_lazy('epi_list')


class EpiUpdate(LoginRequiredMixin, UpdateView):
    """
    View para atualizar um EPI existente.
    """
    model = Epis
    form_class = EpiForm
    template_name = 'epi_shops/epi_form.html'
    success_url = reverse_lazy('epi_list')


class EpiDelete(LoginRequiredMixin, DeleteView):
    """
    View para excluir um EPI.
    """
    model = Epis
    template_name = 'epi_shops/epi_delete.html' # Corrigido: nome do template
    success_url = reverse_lazy('epi_list')


# --- Views para Carrinho ---

@login_required
def add_to_cart(request, pk):
    """
    Adiciona um item ao carrinho ou atualiza a quantidade se o item já existir.
    """
    epi = get_object_or_404(Epis, pk=pk)  # Obtém o EPI pelo ID
    if request.method == 'POST':  # Verifica se a requisição é POST
        form = AddToCartForm(request.POST)  # Cria uma instância do formulário com os dados POST
        if form.is_valid():  # Verifica se o formulário é válido
            quantidade = form.cleaned_data['quantidade']  # Obtém a quantidade do formulário
            carrinho, created = Carrinhos.objects.get_or_create(  # Tenta obter ou criar um item no carrinho
                usuario=request.user, epi=epi, tipo=Carrinhos.COMPRA, defaults={'quantidade': quantidade}
            )
            if not created:  # Se o item já existia no carrinho
                carrinho.quantidade += quantidade  # Atualiza a quantidade
                carrinho.save()  # Salva as alterações no carrinho
            messages.success(request, f'{quantidade} "{epi.nome}" adicionado ao carrinho.') # Mensagem de sucesso
            return redirect(reverse('epi_detail', kwargs={'pk': epi.pk})) # Redireciona para a página de detalhes do EPI

        else:  # Se o formulário for inválido
            for error in form.non_field_errors():  # Itera sobre os erros de formulário
                messages.error(request, error)  # Exibe cada erro como uma mensagem
    else:  # Se a requisição for GET
        form = AddToCartForm(initial={'epi': epi})  # Inicializa o formulário com o EPI

    return render(request, 'epi_shops/add_to_cart.html', {'form': form, 'epi': epi})  # Renderiza o template


@login_required
def view_cart(request):
    """
    Exibe o carrinho de compras e o valor total dos itens.
    """
    carrinho_itens = Carrinhos.objects.filter(usuario=request.user, tipo=Carrinhos.COMPRA)  # Obtém os itens do carrinho do usuário
    valor_total = sum(item.epi.valor * item.quantidade for item in carrinho_itens)  # Calcula o valor total
    return render(request, 'epi_shops/carrinho.html', {'carrinho_itens': carrinho_itens, 'valor_total': valor_total}) # Renderiza o template


@login_required
def remove_from_cart(request, item_id):
    """
    Remove um item do carrinho.
    """
    item = get_object_or_404(Carrinhos, pk=item_id, usuario=request.user)  # Obtém o item do carrinho ou 404
    item.delete()  # Exclui o item
    messages.success(request, f'"{item.epi.nome}" removido do carrinho.') # Mensagem de sucesso
    return redirect('view_cart')  # Redireciona para a view do carrinho


@login_required
def update_cart(request, item_id):
    """
    Atualiza a quantidade de um item no carrinho.
    """
    item = get_object_or_404(Carrinhos, pk=item_id, usuario=request.user)  # Obtém o item do carrinho
    if request.method == 'POST':  # Verifica se é POST
        form = AddToCartForm(request.POST, instance=item)  # Usa o AddToCartForm para atualizar
        if form.is_valid():  # Verifica se é válido
            form.save()  # Salva
            messages.success(request, f'Quantidade de "{item.epi.nome}" atualizada.') # Mensagem de sucesso
            return redirect('view_cart')  # Redireciona para view cart
    else:  # Se for GET
        form = AddToCartForm(instance=item)  # Inicializa com os dados atuais
    return render(request, 'epi_shops/update_cart.html', {'form': form, 'item': item}) # Renderiza o template