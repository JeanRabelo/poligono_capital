# Rates App - Taxas Referenciais B3

## Descrição
Aplicação Django para consultar e armazenar taxas referenciais da BM&FBOVESPA.

## Funcionalidades
- ✅ Interface web com seleção de data
- ✅ Consulta automática ao banco de dados
- ✅ Scraping da página B3 quando dados não existem
- ✅ Armazenamento automático das taxas no banco de dados
- ✅ Exibição em tabela responsiva

## Arquivos Criados

### Backend
- `models.py` - Model B3Rate para armazenar taxas (data, indicador, valor)
- `views.py` - View homepage com lógica de busca e scraping
- `urls.py` - Configuração de URLs da app
- `admin.py` - Interface administrativa para gerenciar taxas
- `apps.py` - Configuração da aplicação

### Frontend
- `templates/rates/homepage.html` - Interface responsiva com:
  - Seletor de data
  - Botão "Buscar taxas dessa data"
  - Tabela de resultados
  - Mensagens de sucesso/erro
  - Design moderno e gradiente

### Migrações
- `0001_initial.py` - Criação da tabela B3Rate

## Como Usar

1. **Acessar a aplicação:**
   ```
   http://127.0.0.1:8000/
   ```

2. **Selecionar uma data:**
   - Use o seletor de data
   - Clique em "🔍 Buscar taxas dessa data"

3. **Visualizar resultados:**
   - Se existir no banco de dados, mostra imediatamente
   - Se não existir, busca da B3 e salva automaticamente
   - Exibe tabela com: Indicador, Valor (%), Data

## Tecnologias Utilizadas
- Django 6.0
- BeautifulSoup4 - Para web scraping
- Requests - Para requisições HTTP
- SQLite - Banco de dados
- HTML/CSS - Interface responsiva

## Modelo de Dados

```python
class B3Rate(models.Model):
    date = DateField()          # Data da taxa
    indicator = CharField()     # Nome do indicador
    value = DecimalField()      # Valor da taxa
    created_at = DateTimeField() # Data de criação do registro
```

## Configurações

A app foi registrada em `settings.py`:
```python
INSTALLED_APPS = [
    ...
    'rates',
]
```

URLs configuradas em `calculadora/urls.py`:
```python
urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('rates.urls')),
]
```

## Admin Interface

Acesse `/admin/` para gerenciar as taxas manualmente:
- Filtros por data
- Busca por indicador
- Visualização organizada

## Notas Importantes

### Web Scraping da B3
O scraper atual é uma implementação base que precisa ser ajustada de acordo com a estrutura real da página B3. A página pode:
- Usar JavaScript para carregar dados (necessitaria Selenium)
- Ter uma API REST ou endpoint de dados
- Usar formato específico de tabelas HTML

**Recomendação:** Inspecionar a página real da B3 para ajustar o scraper conforme necessário.

### Melhorias Futuras
- [ ] Implementar cache de requisições
- [ ] Adicionar gráficos de visualização
- [ ] Exportar dados para CSV/Excel
- [ ] Notificações quando novas taxas são disponibilizadas
- [ ] API REST para integração com outros sistemas
- [ ] Tratamento específico para diferentes tipos de taxas

## Troubleshooting

### Erro ao buscar dados da B3
- Verificar conexão com internet
- Verificar se a URL da B3 está acessível
- Ajustar o scraper conforme estrutura real da página

### Dados não aparecem
- Verificar se as migrações foram aplicadas: `python3 manage.py migrate`
- Verificar logs do servidor no terminal
- Verificar modelo no Django Admin

## Servidor de Desenvolvimento

```bash
# Iniciar servidor
cd solucao
python3 manage.py runserver

# Criar superusuário (para acessar admin)
python3 manage.py createsuperuser

# Aplicar migrações
python3 manage.py makemigrations
python3 manage.py migrate
```

