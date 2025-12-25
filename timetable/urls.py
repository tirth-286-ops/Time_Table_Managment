from django.urls import path
from .views import courses_list, timetable_view, download_pdf, download_excel  

urlpatterns = [
    path('', courses_list, name='courses'),
    path('timetable/<int:course_id>/', timetable_view, name='timetable'),  
    path('timetable/<int:course_id>/pdf/', download_pdf, name='download_pdf'),
    path('timetable/<int:course_id>/excel/', download_excel, name='download_excel'),
]
