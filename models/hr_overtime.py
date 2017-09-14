import time
import pytz
from datetime import datetime,timedelta
from odoo import SUPERUSER_ID
from odoo import models, fields, api, _
from odoo.exceptions import except_orm

class hr_overtime(models.Model):
	_name = "hr.overtime"
	_description = "HR Overtime"
	
	
	
	@api.one
	def _compute_total(self):
		DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
		from_date = datetime.strptime(self.from_date, DATETIME_FORMAT)
		to_date = datetime.strptime(self.to_date, DATETIME_FORMAT)
		timedelta = to_date - from_date
		diff_day = (float(timedelta.seconds) / 86400) * 24
		self.total_time = diff_day
	
	
	name = fields.Char(string="Name", readonly=True)
	employee_id = fields.Many2one('hr.employee', string="Employee", required=True)
	reason = fields.Text(string="Overtime Reason")
	from_date = fields.Datetime(srting="From Date", required=True)
	to_date = fields.Datetime(srting="To Date", required=True)
	actaul_leave_time = fields.Datetime(string="Actual Leave Time", readonly=True)
	total_time = fields.Float(string="Total Time", compute='_compute_total')
	type = fields.Selection([
		('official_leave','Official Leave'),
		('public_holiday','Public Holiday'),
		('working_day','Working Day'),
		('weekend','WeekEnd'),
	], string="Overtime Type")
	
	state = fields.Selection([
		('draft','Draft'),
		('submit','Submitted'),
		('approve','Approved'),
	], string="Status", default= "draft")
	
	@api.model
	def create(self, values):
		values['name'] = self.env['ir.sequence'].get('hr.ov.req') or ' '
		res = super(hr_overtime, self).create(values)
		return res
	
	@api.multi
	def action_sumbit(self):
		return self.write({'state': 'submit'})
	
	@api.multi
	def action_approve(self):
		return self.write({'state': 'approve'})
	@api.multi
	def action_set_to_draft(self):
		return self.write({'state': 'draft'})
		
	@api.onchange('from_date','employee_id')
	def onchange_from_date(self):
		day_list =[]
		type = ''
		DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
		if self.from_date:
			contract_id = self.env['hr.employee'].browse(self.employee_id.id).contract_id.id
			for con in self.env['hr.contract'].browse(contract_id):
				for con_day in con.working_hours.attendance_ids:
					day_list.append(con_day.dayofweek)
			request_date = datetime.strptime(self.from_date, DATETIME_FORMAT).date()
			request_day = request_date.weekday()
			if str(request_day) in day_list:
				type = 'working_day'
			else:
				type = 'weekend'
				
		
			self.type = type
		
	
class hr_overtime_structure(models.Model):
	_name= "hr.overtime.structure"
	_description = "Overtime Structure"
	
	name= fields.Char(string="Structure Name")
	code = fields.Char(string="Code", required=True)
	department_ids = fields.Many2many('hr.department', string="Department (s)")
	overtime_method = fields.Selection([
		('ov_request','According to Request'),
		('ov_attendance','According to Attendance'),
	], string="Overtime Method", required=True)
	hr_ov_structure_rule_ids = fields.One2many('hr.ov.structure.rule','hr_overtime_structure_id', string="Overtime Structure Line")
	state = fields.Selection([
		('draft','Draft'),
		('apply','Applied')
	], string="Status", default="draft")
	
	
	@api.model
	def create(self, values):
		values['name'] = values['name'] + "( " + values['code'] + " )"
		res = super(hr_overtime_structure, self).create(values)
		return res
		
	@api.one
	def apply_ov_structure(self):
		dep_list =[]
		emp_list =[]
		for dep in self.department_ids:
			dep_list.append(dep.id)
		employee_ids = self.env['hr.employee'].search([('department_id','in',dep_list)])
		for emp in employee_ids:
			emp_list.append(emp.id)
		contract_ids = self.env['hr.contract'].search([('employee_id','in',emp_list)])
		for contract in contract_ids:
			contract.write({'overtime_structure_id': self.id})
		self.write({'state':'apply'})
		
		
class hr_ov_structure_rule(models.Model):
	_name = "hr.ov.structure.rule"
	_description = "Overtime Structure Rule"
	
	type = fields.Selection([
		('official_leave','Official Leave'),
		('public_holiday','Public Holiday'),
		('working_day','Working Day'),
		('weekend','WeekEnd')
	], string="Overtime Type", default="working_day")
	
	rate = fields.Float(string="Rate", widget="float_time", required=True, default=1)
	begin_after = fields.Float(string="Begin After")
	
	hr_overtime_structure_id = fields.Many2one('hr.overtime.structure', string="Overtime Structure Ref.", ondelete='cascade')

class hr_contract(models.Model):
	_inherit = "hr.contract"
	
	overtime_structure_id = fields.Many2one('hr.overtime.structure', string="Overtime Structure")
	

class hr_absensi(models.Model):
	_inherit = 'hr.payslip'

	@api.model
	def get_worked_day_lines(self, contract_ids, date_from, date_to):
		res = super(hr_absensi, self).get_worked_day_lines(contract_ids, date_from, date_to)
		user_pool = self.env['res.users']
		contract_obj = self.env['hr.contract']
		attendance_obj = self.env['hr.attendance']
		working_hours_obj = self.env['resource.calendar']
		user = user_pool.browse(SUPERUSER_ID)
		#tz = pytz.timezone(user.partner_id.tz) or pytz.utc
		for contract in contract_obj.browse(contract_ids):
			radit = contract.id
		overtime = {
			'name': 'Absensi',
			'sequence': 11,
			'code': 'Absensi',
			'number_of_days': 240 / 24,
			'number_of_hours': 0,
			'contract_id': contract.id,
		}
		#res += [overtime]
		return res

	
class hr_payroll(models.Model):
	_inherit = 'hr.payslip'
	
	@api.model
	def get_worked_day_lines(self, contract_ids, date_from, date_to):
		res = super(hr_payroll, self).get_worked_day_lines(contract_ids, date_from, date_to)
		
		val_overtime = 0.0
		computed_days = 0.0
		computed_days_total = 0.0
		holidays_overtime = 0.0
		# Objects definitions
		user_pool = self.env['res.users']
		contract_obj = self.env['hr.contract']
		attendance_obj = self.env['hr.attendance']
		working_hours_obj = self.env['resource.calendar']
		
		# Common Variable
		DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
		TIME_FORMAT = "%H:%M:%S"
		
		user = user_pool.browse(SUPERUSER_ID)
		#tz = pytz.timezone(user.partner_id.tz) or pytz.utc
		
		sign_in_date = ""
		sign_in_attendance_time = timedelta(hours=00, minutes=00, seconds=00)
		sign_out_date = ""
		sign_out_attendance_time = timedelta(hours=00, minutes=00, seconds=00)
		
		def is_in_working_schedule(date_in, working_hours_id):
			found = False
			if type(date_in) is datetime:
				working_hours = working_hours_obj.browse(working_hours_id)
				for line in working_hours.attendance_ids:
					if int(line.dayofweek) == date_in.weekday():
						found = True
						break
			return found
			
			
		def get_end_hour_of_the_day(date_in, working_hours_id):
			hour = 0.0
			if type(date_in) is datetime:
				working_hours = working_hours_obj.browse(working_hours_id)
				for line in working_hours.attendance_ids:
					# First assign to hour
					if int(line.dayofweek) == date_in.weekday() and hour == 0.0:
						hour = line.hour_to
					# Other assignments to hour
					# No need for this part but it's a fail safe condition
					elif int(line.dayofweek) == date_in.weekday() and hour != 0.0 and line.hour_from < hour:
						hour = line.hour_to
			return hour
			
		def get_time_from_float(float_time):
			str_time = str(float_time)
			str_hour = str_time.split('.')[0]
			str_minute = ("%2d" % int(str(float("0." + str_time.split('.')[1]) * 60).split('.')[0])).replace(' ','0')
			str_ret_time = str_hour + ":" + str_minute + ":00"
			str_ret_time = datetime.strptime(str_ret_time, TIME_FORMAT).time()
			return str_ret_time
			
		def get_float_from_time(time_type):
			signOnP = [int(n) for n in time_type.split(":")]
			signOnH = signOnP[0] + signOnP[1]/60.0
			return signOnH


		def get_overtime_working_day(time_type):
			totalTime = get_float_from_time(str(time_type))
			if totalTime > 1:
				jamPertama = 1.5
				jamSelanjutnya = (totalTime-1) * 2
				totalJam = jamPertama + jamSelanjutnya
			else:
				totalJam = totalTime*1.5
			return totalJam


		def get_overtime_holiday(time_type):
			totalTime = get_float_from_time(str(time_type))
			if totalTime >= 10:
				jamPertama = 8*2
				jamKedua = 1*3
				jamSelanjutnya = (totalTime-9)*4
				totalJam = jamPertama+jamKedua+jamSelanjutnya
			elif totalTime == 9:
				jamPertama = 8*2
				jamKedua = 1*3
				totalJam = jamPertama+jamKedua
			else:
				totalJam = totalTime*2
			return totalJam

		
		for contract in contract_obj.browse(contract_ids):
			# If work schedule not found skip this contract
			if not contract.working_hours:
				raise except_orm('Error', "Working Schedule is not defined on this %s contract." % contract.name)
				#continue
				
			if not contract.overtime_structure_id:
				raise except_orm('Error', "Overtime structure is not defined on this %s contract." % contract.name)
				#continue
			
			
			if contract.overtime_structure_id.overtime_method == 'ov_attendance':
				# Search and Loop attendance records
				search_domain = [
					('name', '>=', date_from),
					('name', '<=', date_to),
					('employee_id', '=', contract.employee_id.id),
				]
				attendance_ids = attendance_obj.search(search_domain)
				for attendance in attendance_ids:
					# Get localized datetime
					attendance_datetime = pytz.utc.localize(datetime.strptime(attendance.name, DATETIME_FORMAT)).astimezone(tz)
					
					# Get end of day from Working Hours   
					hour_to = get_end_hour_of_the_day(attendance_datetime, contract.working_hours.id)
					hour_to_time = get_time_from_float(hour_to)
					
					holiday_status_id = [self.env['hr.holidays.status'].search([('name','=','Official Leave')]).id,self.env['hr.holidays.status'].search([('name','=','Public Holiday')]).id]
					
					domain =[
						('employee_id','=',attendance.employee_id.id),
						('holiday_status_id','in',holiday_status_id)
					]
					leave_ids = self.env['hr.holidays'].search(domain)
					Flage = False
					for leave in leave_ids:
						leave_datetime = datetime.strptime(leave.date_from, DATETIME_FORMAT)
						leave_date = leave_datetime.date()
						if attendance_datetime.date() == leave_datetime.date():
							Flage = True
						
					
					for rule in contract.overtime_structure_id.hr_ov_structure_rule_ids:
						# First condition overtime in Working Day 
						if is_in_working_schedule(attendance_datetime, contract.working_hours.id):
							if Flage == False:
								if rule.type == 'working_day':
									if attendance.action == 'sign_out':
										start_overtime = hour_to
										start_overtime_time = get_time_from_float(start_overtime)
										start_overtime = tz.localize(datetime.combine(attendance_datetime.date(), start_overtime_time))
										if start_overtime > attendance_datetime:
											continue 
										diff_time = attendance_datetime - start_overtime
										diff_time = get_float_from_time(str(diff_time)) * rule.rate
										diff_time = get_time_from_float(diff_time)
										diff_time = get_overtime_working_day(diff_time)
										val_overtime += diff_time

								elif rule.type == 'public_holiday':
									if attendance.action == 'sign_in':
										sign_in_date = attendance_datetime.date()
										sign_in_attendance_time = attendance_datetime
									
									elif attendance.action == 'sign_out':
										sign_out_date = attendance_datetime.date()
										sign_out_attendance_time = attendance_datetime
									
									if sign_in_date == sign_out_date:
										diff_time = sign_out_attendance_time - sign_in_attendance_time
										diff_time = get_float_from_time(str(diff_time)) * rule.rate
										diff_time = get_time_from_float(diff_time)
										diff_time = get_overtime_holiday(diff_time)
										val_overtime += diff_time
							else:
								if rule.type == 'official_leave':
									if attendance.action == 'sign_in':
										sign_in_date = attendance_datetime.date()
										sign_in_attendance_time = attendance_datetime
									
									elif attendance.action == 'sign_out':
										sign_out_date = attendance_datetime.date()
										sign_out_attendance_time = attendance_datetime
									
									if sign_in_date == sign_out_date:
										diff_time = sign_out_attendance_time - sign_in_attendance_time
										diff_time = get_float_from_time(str(diff_time)) * rule.rate
										diff_time = get_time_from_float(diff_time)
										diff_time = get_overtime_holiday(diff_time)
										val_overtime += diff_time

								elif rule.type == 'public_holiday':
									if attendance.action == 'sign_in':
										sign_in_date = attendance_datetime.date()
										sign_in_attendance_time = attendance_datetime
									
									elif attendance.action == 'sign_out':
										sign_out_date = attendance_datetime.date()
										sign_out_attendance_time = attendance_datetime
									
									if sign_in_date == sign_out_date:
										diff_time = sign_out_attendance_time - sign_in_attendance_time
										diff_time = get_float_from_time(str(diff_time)) * rule.rate
										diff_time = get_time_from_float(diff_time)
										diff_time = get_overtime_holiday(diff_time)
										val_overtime += diff_time
						else:
							if rule.type == 'weekend':
								if attendance.action == 'sign_in':
									sign_in_date = attendance_datetime.date()
									sign_in_attendance_time = attendance_datetime
								
								elif attendance.action == 'sign_out':
									sign_out_date = attendance_datetime.date()
									sign_out_attendance_time = attendance_datetime
								
								if sign_in_date == sign_out_date:
									diff_time = sign_out_attendance_time - sign_in_attendance_time
									diff_time = get_float_from_time(str(diff_time)) * rule.rate
									diff_time = get_time_from_float(diff_time)
									diff_time = get_overtime_holiday(diff_time)
									val_overtime += diff_time
			
			else:
				for rule in contract.overtime_structure_id.hr_ov_structure_rule_ids:
					for overtime in self.env['hr.overtime'].search([('employee_id','=',contract.employee_id.id),('from_date','>=',date_from),('to_date','<=',date_to)]):
						if rule.type == overtime.type:
							if overtime.state == 'approve':
								if overtime.type == 'public_holiday':
									diff_days = computed_days+1
									diff_days_total = computed_days_total+1
									diff_time = overtime.total_time * rule.rate
									diff_time = get_time_from_float(diff_time)
									diff_time = get_overtime_holiday(diff_time)
									val_overtime += diff_time
									holidays_overtime += diff_time
									computed_days = diff_days
									computed_days_total = diff_days_total
								elif overtime.type == 'weekend':
									diff_days = computed_days+1
									diff_days_total = computed_days_total+1
									diff_time = overtime.total_time * rule.rate
									diff_time = get_time_from_float(diff_time)
									diff_time = get_overtime_holiday(diff_time)
									val_overtime += diff_time
									holidays_overtime += diff_time
									computed_days = diff_days
									computed_days_total = diff_days_total
								elif overtime.type =='official_leave':
									diff_days = computed_days+1
									diff_days_total = computed_days_total+1
									diff_time = overtime.total_time * rule.rate
									diff_time = get_time_from_float(diff_time)
									diff_time = get_overtime_holiday(diff_time)
									val_overtime += diff_time
									holidays_overtime += diff_time
									computed_days = diff_days
									computed_days_total = diff_days_total
								else:
									diff_days_total = computed_days_total+1
									val_overtime += overtime.total_time * rule.rate
									computed_days_total = diff_days_total
					
					
					
		overtime = {
			'name': 'Overtime Total',
			'sequence': 11,
			'code': 'Overtime',
			'number_of_days':  computed_days_total,
			'number_of_hours': val_overtime,
			'contract_id': contract.id,
		}
		overtime_libur = {
			'name': 'Overtime Hari Libur',
			'sequence': 12,
			'code': 'HOL',
			'number_of_days':  computed_days,
			'number_of_hours': holidays_overtime,
			'contract_id': contract.id,
		}
		res += [overtime]
		res += [overtime_libur]
		return res
		
class hr_attendance(models.Model):
	_inherit = "hr.attendance"
	
	@api.model
	def create(self, values):
		res = super(hr_attendance, self).create(values)
		employee_id = values['employee_id']
		if values['check_out']:
			check_out = values['check_out']
			overtime_ids = self.env['hr.overtime'].search([('employee_id','=', employee_id),('from_date','<=', check_out),('to_date','>=', check_out)])
			for ov in overtime_ids:
				ov.write({'actaul_leave_time': check_out})
		return res
