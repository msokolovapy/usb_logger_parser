import xlsxwriter

workbook = xlsxwriter.Workbook('scatter.xlsx')
worksheet = workbook.add_worksheet()

# Write data
data = [
    ['ACPL123_234', 1, 25.5],
    ['ACPL123_234', 2, 26.1],
    ['ACPL567_890', 1, 24.8],
    ['ACPL567_890', 2, 25.3],
]

for row_num, row_data in enumerate(data):
    worksheet.write_row(row_num, 0, row_data)

# Create scatter chart
chart = workbook.add_chart({'type': 'scatter', 'subtype': 'straight_with_markers'})

# Add series (works reliably even with single series)
chart.add_series({
    'name': 'ACPL123_234',
    'categories': '=Sheet1!$B$1:$B$2',
    'values': '=Sheet1!$C$1:$C$2',
})

chart.set_title({'name': 'Temperature Data'})
chart.set_x_axis({'name': 'Row'})
chart.set_y_axis({'name': 'Temperature (°C)'})

worksheet.insert_chart('E2', chart)
workbook.close()