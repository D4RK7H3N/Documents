from django.contrib import admin
from .models import DormBuilding, DormRoom, DormAssignment, DormPayment

admin.site.register(DormBuilding)
admin.site.register(DormRoom)
admin.site.register(DormAssignment)
admin.site.register(DormPayment)