{
	'name' : 'Overtime Management',
	'version' : '0.1',
	'author' : 'Primeforce Indonesia',
	'category' : 'Human Resources',
	'depends' : ['hr', 'hr_contract','hr_payroll'],
	'data': [
		'sequences/hr_overtime_sequence.xml',
		'datas/hr_payroll_rule.xml',
		'views/hr_overtime_view.xml',
		'reports/report_view.xml',
		'reports/hr_attendance_analysis_report.xml',
		'wizards/views/hr_attendance_report_view.xml',
	],

	'installable': True,
	'auto_install': False,
}

