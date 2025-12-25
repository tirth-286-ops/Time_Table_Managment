from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from .models import Faculty, Course, Subject, TimetableEntry, TimetablePrintDate

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('name', 'semester', 'classroom')
    list_filter = ('semester',)
    search_fields = ('name',)

@admin.register(Faculty)
class FacultyAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'course', 'faculty', 'track', 'is_common')
    list_filter = ('course', 'track', 'is_common')
    search_fields = ('name', 'faculty__name')

@admin.register(TimetableEntry)
class TimetableEntryAdmin(admin.ModelAdmin):
    list_display = (
        'course', 'day', 'start_time', 'end_time', 'subject', 'faculty',
        'is_break', 'is_lab', 'lab_choice'
    )
    list_filter = ('course', 'day', 'is_break', 'is_lab', 'lab_choice')
    search_fields = ('course__name', 'subject__name', 'faculty__name')
    ordering = ('course', 'day', 'start_time')

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.is_break:
            return ('subject', 'faculty', 'is_lab', 'lab_choice')
        elif obj and obj.is_lab:
            return ('is_break',)
        return ()

@admin.register(TimetablePrintDate)
class TimetablePrintDateAdmin(admin.ModelAdmin):
    list_display = ('course', 'effective_date')
    list_filter = ('course',)
    search_fields = ('course__name',)
