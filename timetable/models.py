from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError

class Course(models.Model):
    name = models.CharField(max_length=100)
    semester = models.IntegerField()
    classroom = models.CharField(max_length=50, blank=True, null=True) 

    def __str__(self):
        return f"{self.name} (Sem {self.semester})"

class Faculty(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class Subject(models.Model):
    name = models.CharField(max_length=100)
    faculty = models.ForeignKey(Faculty, on_delete=models.SET_NULL, null=True, blank=True)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    track = models.CharField(max_length=50, choices=[('AI-ML', 'AI-ML'), ('Web', 'Web')], null=True, blank=True)
    is_common = models.BooleanField(default=False)

    def clean(self):
        if self.track is None and not self.is_common and self.course.semester > 1:
            raise ValidationError('Please specify a track (AI-ML or Web) for this subject in later semesters.')

    def __str__(self):
        return f"{self.name} ({self.course.name})"

class TimetableEntry(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    day = models.CharField(
        max_length=20,
        choices=[('Monday', 'Monday'), ('Tuesday', 'Tuesday'), ('Wednesday', 'Wednesday'),
                 ('Thursday', 'Thursday'), ('Friday', 'Friday'), ('Saturday', 'Saturday')]
    )
    start_time = models.TimeField()
    end_time = models.TimeField()
    subject = models.ForeignKey(Subject, on_delete=models.SET_NULL, null=True, blank=True)
    faculty = models.ForeignKey(Faculty, on_delete=models.SET_NULL, null=True, blank=True)
    is_break = models.BooleanField(default=False)
    is_lab = models.BooleanField(default=False)
    lab_choice = models.CharField(
        max_length=10,
        choices=[('Lab 1', 'Lab 1'), ('Lab 2', 'Lab 2'), ('Lab 3', 'Lab 3'), ('Lab 4', 'Lab 4')],
        blank=True,
        null=True
    )

    def clean(self):
        """Validation logic to prevent conflicts"""
        if not self.is_break and not self.is_lab and (not self.subject or not self.faculty):
            raise ValidationError("A lecture must have both a subject and a faculty unless it's a break or lab.")

        if self.is_lab and not self.lab_choice:
            raise ValidationError("Please select a lab for the lab session.")

        existing_entries = TimetableEntry.objects.filter(
            course=self.course,
            day=self.day,
            start_time__lt=self.end_time,
            end_time__gt=self.start_time
        ).exclude(id=self.id)  

        if not self.is_break and not self.is_lab:
            existing_entries = existing_entries.exclude(is_break=True).exclude(is_lab=True)

            if self.subject and not self.subject.is_common:
                existing_entries = existing_entries.filter(
                    subject__track=self.subject.track
                )

            if existing_entries.exists():
                raise ValidationError(
                    f"Time slot {self.start_time}-{self.end_time} on {self.day} is already booked "
                    f"for this course in the same track."
                )

        if self.faculty:
            faculty_conflicts = TimetableEntry.objects.filter(
                faculty=self.faculty,
                day=self.day,
                start_time__lt=self.end_time,
                end_time__gt=self.start_time
            ).exclude(id=self.id)

            if faculty_conflicts.exists():
                raise ValidationError(
                    f"Faculty {self.faculty.name} is already allocated to another course at this time!"
                )

    def __str__(self):
        return f"{self.course.name} - {self.day} {self.start_time}-{self.end_time}"


class TimetablePrintDate(models.Model):
    course = models.OneToOneField('Course', on_delete=models.CASCADE)
    effective_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.course.name} - Effective from {self.effective_date}"
