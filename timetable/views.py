from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from django.db.models import Q
from datetime import date
from collections import defaultdict
import pandas as pd
import io

from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER

from .models import Course, TimetableEntry, TimetablePrintDate


def courses_list(request):
    query = request.GET.get('q', '').strip()
    courses = Course.objects.all()

    if query:
        if query.isdigit():
            courses = courses.filter(semester=int(query))
        else:
            courses = courses.filter(Q(name__istartswith=query) | Q(name__icontains=query))

    return render(request, 'courses.html', {'courses': courses, 'query': query})

def timetable_view(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    timetable_entries = TimetableEntry.objects.filter(course=course).order_by('start_time')

    grouped_entries = defaultdict(lambda: defaultdict(list))
    subjects_faculty = {}
    time_slots_set = set()

    for entry in timetable_entries:
        start = entry.start_time.strftime("%H:%M")
        end = entry.end_time.strftime("%H:%M")
        time_slot = (start, end)
        grouped_entries[entry.day][time_slot].append(entry)
        time_slots_set.add(time_slot)

        if entry.subject and entry.faculty and entry.subject.name not in subjects_faculty:
            subjects_faculty[entry.subject.name] = entry.faculty.name

    print_info = TimetablePrintDate.objects.filter(course=course).first()

    context = {
        'course': course,
        'timetable_entries': grouped_entries,
        'subjects_faculty': subjects_faculty,
        'days': ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"],
        'time_slots': sorted(time_slots_set),
        'current_date': date.today().strftime('%d-%m-%Y'),
        'effective_note': print_info.effective_date if print_info else None,
    }

    return render(request, 'timetable/timetable.html', context)


def download_pdf(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    print_info = TimetablePrintDate.objects.filter(course=course).first()

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Timetable_{course.name}_Sem{course.semester}.pdf"'

    doc = SimpleDocTemplate(response, pagesize=landscape(letter))
    elements = []
    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        'TitleCenter',
        parent=styles['Title'],
        fontSize=25,            # Bigger font size
        alignment=TA_CENTER     # Center alignment
    )
    effective_style = ParagraphStyle(
        'EffectiveCenter',
        parent=styles['Normal'],
        fontSize=15,
        alignment=TA_CENTER
    )
    heading3_center = ParagraphStyle(
        'Heading3Center',
        parent=styles['Heading3'],
        alignment=TA_CENTER
    )

    # Title
    elements.append(Paragraph(f"Timetable for {course.name} (Sem {course.semester})", title_style))

    # Effective From Note (centered)
    if print_info and print_info.effective_date:
        elements.append(Paragraph(f"<b>Effective From:</b> {print_info.effective_date.strftime('%d-%m-%Y')}", effective_style))

    # Classroom info (centered)
    if course.classroom:
        elements.append(Paragraph(f"Classroom: {course.classroom}", heading3_center))

    elements.append(Spacer(1, 12))

    # Prepare timetable data
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    time_slots = list(
        TimetableEntry.objects.filter(course=course)
        .order_by('start_time')
        .values_list('start_time', 'end_time')
        .distinct()
    )
    timetable_entries = TimetableEntry.objects.filter(course=course).order_by('day', 'start_time')

    timetable = {day: {} for day in days}
    for entry in timetable_entries:
        timetable[entry.day][entry.start_time] = entry

    table_data = [['Time'] + days]

    for start, end in time_slots:
        row = [f"{start.strftime('%I:%M %p')} - {end.strftime('%I:%M %p')}"]
        for day in days:
            entry = timetable.get(day, {}).get(start)
            if entry:
                if entry.is_break:
                    row.append("Break")
                elif entry.is_lab:
                    text = f"Lab {entry.lab_choice}\n{entry.subject.name}"
                    if entry.subject.track:
                        text += f" ({entry.subject.track})"
                    row.append(text)
                elif entry.subject and entry.faculty:
                    text = f"{entry.subject.name}"
                    if entry.subject.track:
                        text += f" ({entry.subject.track})"
                    text += f"\n({entry.faculty.name})"
                    row.append(text)
                else:
                    row.append("-")
            else:
                row.append("-")
        table_data.append(row)

    # Timetable Table Styling
    table = Table(table_data)
    table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ]))
    elements.append(table)

    elements.append(Spacer(1, 24))
    elements.append(Paragraph("Subjects & Faculty", heading3_center))

    # Subjects and Faculty Table
    subjects_faculty = {}
    for entry in timetable_entries:
        if entry.subject and entry.faculty:
            subjects_faculty[entry.subject.name] = entry.faculty.name

    faculty_table_data = [['Subject', 'Faculty']]
    if subjects_faculty:
        for subject, faculty in subjects_faculty.items():
            faculty_table_data.append([subject, faculty])
    else:
        faculty_table_data.append(["No subjects assigned yet", ""])

    faculty_table = Table(faculty_table_data)
    faculty_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ]))
    elements.append(faculty_table)

    doc.build(elements)
    return response

def download_excel(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="Timetable_{course.name}_Sem{course.semester}.xlsx"'

    timetable_entries = TimetableEntry.objects.filter(course=course).order_by('day', 'start_time')
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    time_slots = list(TimetableEntry.objects.filter(course=course).order_by('start_time').values_list('start_time', 'end_time').distinct())

    timetable = {day: {} for day in days}
    for entry in timetable_entries:
        timetable[entry.day][entry.start_time] = entry

    table_data = [['Time'] + days]
    for start, end in time_slots:
        row = [f"{start.strftime('%I:%M %p')} - {end.strftime('%I:%M %p')}"]
        for day in days:
            entry = timetable.get(day, {}).get(start)
            if entry:
                if entry.is_break:
                    row.append("Break")
                elif entry.is_lab:
                    row.append(f"Lab {entry.lab_choice}\n{entry.subject.name}")
                elif entry.subject and entry.faculty:
                    row.append(f"{entry.subject.name}\n({entry.faculty.name})")
                else:
                    row.append("-")
            else:
                row.append("-")
        table_data.append(row)

    df_timetable = pd.DataFrame(table_data[1:], columns=table_data[0])

    subjects_faculty_data = [['Subject', 'Faculty']]
    subjects_faculty = TimetableEntry.objects.filter(course=course).values_list('subject__name', 'faculty__name').distinct()
    for subject, faculty in subjects_faculty:
        if subject and faculty and faculty != "None":
            subjects_faculty_data.append([subject, faculty])

    df_subjects_faculty = pd.DataFrame(subjects_faculty_data[1:], columns=subjects_faculty_data[0])

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook = writer.book
        worksheet = workbook.add_worksheet('Timetable')
        writer.sheets['Timetable'] = worksheet

        format_table(worksheet, df_timetable, df_subjects_faculty, workbook)

    output.seek(0)
    response.write(output.read())
    return response


def format_table(worksheet, df_timetable, df_subjects_faculty, workbook):
    format_header = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#D3D3D3', 'border': 1})
    format_cell = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1})

    col_widths = [20] + [30] * (len(df_timetable.columns) - 1)
    for i, width in enumerate(col_widths):
        worksheet.set_column(i, i, width)

    row_offset = 0
    for col_num, value in enumerate(df_timetable.columns.values):
        worksheet.write(row_offset, col_num, value, format_header)

    for row_num, row in df_timetable.iterrows():
        for col_num, value in enumerate(row):
            worksheet.write(row_num + row_offset + 1, col_num, value, format_cell)

    row_offset += len(df_timetable) + 3

    worksheet.set_column(0, 0, 40)
    worksheet.set_column(1, 1, 40)

    for col_num, value in enumerate(df_subjects_faculty.columns.values):
        worksheet.write(row_offset, col_num, value, format_header)

    for row_num, row in df_subjects_faculty.iterrows():
        for col_num, value in enumerate(row):
            worksheet.write(row_num + row_offset + 1, col_num, value, format_cell)
