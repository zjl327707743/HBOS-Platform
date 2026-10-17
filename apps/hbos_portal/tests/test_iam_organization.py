"""Synthetic source validation and presentation grouping; no private source rows."""
from __future__ import annotations
import types
import unittest
from unittest.mock import patch
from .test_iam_policy import Invalid, PermissionDenied, Attr
from hbos_portal.iam import organization

class OrganizationContractTest(unittest.TestCase):
    def setUp(self):
        def throw(message, kind=Invalid): raise kind(message)
        self.fake=types.SimpleNamespace(throw=throw,ValidationError=Invalid,PermissionError=PermissionDenied,conf=Attr(hbos_iam_test_site=1),session=Attr(user='Administrator'),local=Attr(site='iam-r4-b.localhost',request=None))
        self.patcher=patch.object(organization,'frappe',self.fake);self.patcher.start();self.addCleanup(self.patcher.stop)
        self.company=dict(name='合成公司',abbr='SYN',country='China',default_currency='CNY')
        self.nodes=[dict(key='root',name='合成公司',parent=None,is_group=1,source_rows=[3]),dict(key='root/d1',name='合成部门甲',parent='root',is_group=0,source_rows=[3])]
    def test_clear_source_tree_accepts_only_complete_explicit_native_metadata(self):
        organization.validate_source_plan(self.company,self.nodes,'a'*64)
        for company,nodes,sha in [({**self.company,'user':'fake'},self.nodes,'a'*64),(self.company,self.nodes,'not-sha'),(self.company,[self.nodes[1]],'a'*64),(self.company,[self.nodes[0],{**self.nodes[1],'name':self.nodes[0]['name']}],'a'*64),(self.company,[{**self.nodes[0],'is_group':0},self.nodes[1]],'a'*64)]:
            with self.subTest(sha=sha),self.assertRaises(Invalid):organization.validate_source_plan(company,nodes,sha)
    def test_groups_use_explicit_ids_and_cannot_become_an_authorization_input(self):
        conf=Attr(hbos_iam_test_site=1,hbos_iam_technical_employee_ids=['EMP-tech'])
        rows=[Attr(name='EMP-real',employee_name='C03 Synthetic Name'),Attr(name='EMP-tech',employee_name='普通中文姓名')]
        self.assertEqual([r.name for r in organization.filter_rows(rows,'Employee',conf=conf)],['EMP-real'])
        self.assertEqual([r.name for r in organization.filter_rows(rows,'Employee','technical',conf=conf)],['EMP-tech'])
        self.assertEqual(organization.filter_rows(rows,'Employee','all',conf=conf),rows)
        self.assertEqual(organization.technical_ids('Employee',Attr(hbos_iam_test_site=0,hbos_iam_technical_employee_ids=['EMP-real'])),[])
    def test_native_preparation_is_not_whitelisted_or_available_from_http(self):
        self.assertFalse(getattr(organization.apply_source_organization,'allow_guest',False))
        with patch.object(organization,'require_isolated_site'):
            for user,request in [('ordinary',None),('Administrator',object())]:
                self.fake.session.user=user;self.fake.local.request=request
                with self.assertRaises(PermissionDenied):organization._root()
