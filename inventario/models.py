from django.db import models # type: ignore
from django.contrib.auth.models import Group, User# type: ignore
from decimal import Decimal

class LoteBipagem(models.Model):
    id=models.AutoField(primary_key=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    STATUS_CHOICES = [
        ('aberto', 'Aberto'),
        ('fechado', 'Fechado'),
        ('aguardando validação', 'Aguardando Validação'),
        ('invalidado', 'Invalidado'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Aberto')
    user_created = models.ForeignKey('auth.User', on_delete=models.CASCADE,null=True)
    group_user_txt = models.CharField(max_length=100, default='grupo_padrao')
    group_user = models.ForeignKey(Group, null=True, blank=True, on_delete=models.SET_NULL)
    numero_lote = models.IntegerField(default = 1)

class Caixa(models.Model):
    id=models.AutoField(primary_key=True)
    nr_caixa = models.CharField(max_length=100,null=True)
    lote = models.ForeignKey(LoteBipagem, on_delete=models.CASCADE, related_name='caixas')
    identificador = models.CharField(max_length=100)
    descricao = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    STATUS_CHOICES = [
        ('iniciada', 'Iniciada'),
        ('finalizada', 'Finalizada'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Iniciada')

    def __str__(self):
        return f"Caixa {self.identificador} (Lote #{self.lote.id})"
    

class Bipagem(models.Model):
    id = models.AutoField(primary_key=True)
    id_caixa = models.ForeignKey(Caixa, on_delete=models.CASCADE, related_name='bipagem')
    id_lote = models.ForeignKey(LoteBipagem, on_delete=models.CASCADE, related_name='bipagem')
    group_user = models.ForeignKey(Group, on_delete=models.CASCADE, null=True)
    user_created = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    unidade = models.IntegerField(null=True)
    nrserie = models.CharField(max_length=50)
    criado_em = models.DateTimeField(auto_now_add=True)
    modelo = models.CharField(max_length=100, null=True)
    ESTADO_CHOICES = [
        ('GOOD', 'GOOD'),
        ('BAD', 'BAD'),
        ('TRIAGEM', 'TRIAGEM'),
        ('OBSOLETO', 'OBSOLETO'),
        ('SUCATA', 'SUCATA'),
        ('REVERSA', 'REVERSA'),
        ('KIT GOOD', 'KIT GOOD'),
    ]
    estado = models.CharField(max_length=100, choices=ESTADO_CHOICES, blank=True, null=True)
    patrimonio = models.CharField(max_length=100, null=True)
    mensagem_ferramenta_inv = models.CharField(max_length=255, blank=True, null=True)
    observacao = models.CharField(max_length=255, blank=True, null=True)
    comentarios = models.CharField(max_length=250, blank=True, null=True)

class Serial(models.Model):
    codigo = models.CharField(max_length=100, unique=True)
    lote = models.ForeignKey(LoteBipagem, on_delete=models.CASCADE, related_name='seriais')

    def __str__(self):
        return self.codigo
    
class PontoAtendimentoInfo(models.Model):
    group = models.OneToOneField(Group, on_delete=models.CASCADE, related_name='informacoes')
    endereco = models.CharField(max_length=255, verbose_name="Endereço")
    limite = models.IntegerField(verbose_name="Limite de bipagens", default=50)
    liberado = models.BooleanField(default=False, verbose_name="Acesso liberado")

    def __str__(self):
        return f"{self.group.name} - {self.endereco}"
    
def _extracao_diaria_upload_to(instance, filename):
    return f"extracoes_auditoria/{instance.data_referencia:%Y/%m/%d}/{instance.group.name}/{filename}"


class ExtracaoDiariaAuditoria(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="extracoes_diarias")
    data_referencia = models.DateField(verbose_name="Data de referência")
    arquivo_csv = models.FileField(upload_to=_extracao_diaria_upload_to)
    total_seriais = models.PositiveIntegerField(default=0)
    gerado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Extração diária de auditoria"
        verbose_name_plural = "Extrações diárias de auditoria"
        constraints = [
            models.UniqueConstraint(
                fields=["group", "data_referencia"],
                name="uniq_extracao_diaria_por_pa_data",
            ),
        ]
        ordering = ["-data_referencia", "group__name"]

    def __str__(self):
        return f"{self.group.name} - {self.data_referencia:%d/%m/%Y}"


class InventarioDadosImportados(models.Model):
    serial = models.CharField(max_length=100, primary_key=True)
    modelo = models.CharField(max_length=200)
    serial_fabricante = models.CharField(max_length=100)
    nome_ct = models.CharField(max_length=100, null=True, blank=True)
    mensagem_ferramenta_inv = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        db_table = 'inventario_dados_importados'
        verbose_name = "Inventário Importado"
        verbose_name_plural = "Inventários Importados"

    def __str__(self):
        return f"{self.serial} - {self.modelo}"