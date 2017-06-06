from openerp.osv import fields, osv
from datetime import date

class hr_attendance_reporting(osv.osv_memory):
	_name = "hr.attendance.reporting"
	_description = "HR  Attendance Report Wizard"
	
	_columns = {
		'attandance_report_id': fields.many2one('ir.actions.report.xml', required=True, string="Report Name", domain=[('model', '=', 'hr.attendance')]),
		'employee_id': fields.many2one('hr.employee', required=True, string="Employee"),
		'date_from': fields.date(string="From", required=True),
		'date_to': fields.date(string="To", required=True),
	}
	
	_defaults={
		'date_to': fields.date.today(),
	}
	
	def action_print(self, cr, uid, ids, context=None):
		res = {}
		for wizard in self.browse(cr, uid, ids, context):
			report_name= wizard.attandance_report_id.report_name
			datas = {
				'ids': self.pool.get('hr.attendance').search(cr, uid, [('employee_id.name','=',wizard.employee_id.name),('name','>=',wizard.date_from),('name','<',wizard.date_to)], order="name",context=context),
				'model': 'hr.attendance',
				'form': self.read(cr, uid, ids, [], context=context)
				}
			res = {
				'type': 'ir.actions.report.xml',
				'report_name': report_name,
				'datas': datas,
				}
		return res
