
import functools
import ctypes


from winstructs import *
from windef import *



_GUID = IID
class IID(IID):
    def __init__(self, Data1=None, Data2=None, Data3=None, Data4=None, name=None, strid=None):
        data_tuple = (Data1, Data2, Data3, Data4)
        self.name = name
        self.strid = strid
        if all(data is None for data in data_tuple):
            return super(IID, self).__init__()
        if any(data is None for data in data_tuple):
            raise ValueError("All or none of (Data1, Data2, Data3, Data4) should be None")
        super(IID, self).__init__(Data1, Data2, Data3, Data4)

    def __repr__(self):
        notpresent = object()
        # Handle IID created without '__init__' (like ctypes-ptr deref)
        if getattr(self, "strid", notpresent) is notpresent:
            self.strid = self.to_string()
        if self.strid is None:
            return super(IID, self).__repr__()

        if getattr(self, "name", notpresent) is notpresent:
            self.name = None
        if self.name is None:
            return '<IID "{0}">'.format(self.strid.upper())
        return '<IID "{0}({1})">'.format(self.strid.upper(), self.name)

    def to_string(self):
        data4_format = "{0:02X}{1:02X}-" + "".join("{{{i}:02X}}".format(i=i + 2) for i in range(6))
        data4_str = data4_format.format(*self.Data4)
        return "{0:08X}-{1:04X}-{2:04X}-".format(self.Data1, self.Data2, self.Data3) + data4_str

    def update_strid(self):
       new_strid = self.to_string()
       self.strid = new_strid

    @classmethod
    def from_string(cls, iid):
        part_iid = iid.split("-")
        datas = [int(x, 16) for x in part_iid[:3]]
        datas.append(int(part_iid[3][:2], 16))
        datas.append(int(part_iid[3][2:], 16))
        for i in range(6):
            datas.append(int(part_iid[4][i * 2:(i + 1) * 2], 16))
        return cls.from_raw(*datas, strid=iid)

    @classmethod
    def from_raw(cls, Data1, Data2, Data3, Data41, Data42, Data43, Data44, Data45, Data46, Data47, Data48, **kwargs):
        return cls(Data1, Data2, Data3,  (BYTE*8)(Data41, Data42, Data43, Data44, Data45, Data46, Data47, Data48), **kwargs)

    def __eq__(self, other):
        if not isinstance(other, (IID, _GUID)):
            return NotImplemented
        return (self.Data1, self.Data2, self.Data3, self.Data4[:]) == (other.Data1, other.Data2, other.Data3, other.Data4[:])

generate_IID = IID.from_raw

GUID = IID
LPGUID = POINTER(GUID)
REFGUID = POINTER(GUID)
REFCLSID = POINTER(GUID)
REFIID = POINTER(GUID)

class COMInterface(ctypes.c_void_p):
    _functions_ = {
    }

    def __getattr__(self, name):
        if name in self._functions_:
            return functools.partial(self._functions_[name], self)
        return super(COMInterface, self).__getattribute__(name)

class COMImplementation(object):
    IMPLEMENT = None

    def get_index_of_method(self, method):
        # This code is horrible but not totally my fault
        # the PyCFuncPtrObject->index is not exposed to Python..
        # repr is: '<COM method offset 2: WinFunctionType at 0x035DDBE8>'
        rpr = repr(method)
        if not rpr.startswith("<COM method offset ") or ":" not in rpr:
            raise ValueError("Could not extract offset of {0}".format(rpr))
        return int(rpr[len("<COM method offset "): rpr.index(":")])

    def extract_methods_order(self, interface):
        index_and_method = sorted((self.get_index_of_method(m),name, m) for name, m in interface._functions_.items())
        return index_and_method

    def verify_implem(self, interface):
        for func_name in interface._functions_:
            implem = getattr(self, func_name, None)
            if implem is None:
                raise ValueError("<{0}> implementing <{1}> has no method <{2}>".format(type(self).__name__, self.IMPLEMENT.__name__, func_name))
            if not callable(implem):
                raise ValueError("{0} implementing <{1}>: <{2}> is not callable".format(type(self).__name__, self.IMPLEMENT.__name__, func_name))
        return True

    def _create_vtable(self, interface):
        implems = []
        names = []
        for index, name, method in self.extract_methods_order(interface):
            func_implem = getattr(self, name)
            #PVOID is 'this'
            types = [method.restype, PVOID] + list(method.argtypes)
            implems.append(ctypes.WINFUNCTYPE(*types)(func_implem))
            names.append(name)
        class Vtable(ctypes.Structure):
            _fields_ = [(name, ctypes.c_void_p) for name in names]
        return Vtable(*[ctypes.cast(x, ctypes.c_void_p) for x in implems]), implems

    def __init__(self):
        self.verify_implem(self.IMPLEMENT)
        vtable, implems = self._create_vtable(self.IMPLEMENT)
        self.vtable = vtable
        self.implems = implems
        self.vtable_pointer = ctypes.pointer(self.vtable)
        self._as_parameter_ = ctypes.addressof(self.vtable_pointer)

    def QueryInterface(self, this, piid, result):
        if piid[0] in (IUnknown.IID, self.IMPLEMENT.IID):
            result[0] = this
            return 1
        return E_NOINTERFACE

    def AddRef(self, *args):
        return 1

    def Release(self, *args):
        return 0

class IBackgroundCopyCallback(COMInterface):
    IID = generate_IID(0x97EA99C7, 0x0186, 0x4AD4, 0x8D, 0xF9, 0xC5, 0xB4, 0xE0, 0xED, 0x6B, 0x22, name="IBackgroundCopyCallback", strid="97EA99C7-0186-4AD4-8DF9-C5B4E0ED6B22")

    _functions_ = {
 #QueryInterface -> riid:REFIID, ppvObject:**void
 "QueryInterface": ctypes.WINFUNCTYPE(HRESULT, REFIID, POINTER(PVOID))(0, "QueryInterface"),
 #AddRef -> 
 "AddRef": ctypes.WINFUNCTYPE(ULONG)(1, "AddRef"),
 #Release -> 
 "Release": ctypes.WINFUNCTYPE(ULONG)(2, "Release"),
 #JobTransferred -> pJob:*IBackgroundCopyJob
 "JobTransferred": ctypes.WINFUNCTYPE(HRESULT, PVOID)(3, "JobTransferred"),
 #JobError -> pJob:*IBackgroundCopyJob, pError:*IBackgroundCopyError
 "JobError": ctypes.WINFUNCTYPE(HRESULT, PVOID, PVOID)(4, "JobError"),
 #JobModification -> pJob:*IBackgroundCopyJob, dwReserved:DWORD
 "JobModification": ctypes.WINFUNCTYPE(HRESULT, PVOID, DWORD)(5, "JobModification"),
    }


class IBackgroundCopyError(COMInterface):
    IID = generate_IID(0x19C613A0, 0xFCB8, 0x4F28, 0x81, 0xAE, 0x89, 0x7C, 0x3D, 0x07, 0x8F, 0x81, name="IBackgroundCopyError", strid="19C613A0-FCB8-4F28-81AE-897C3D078F81")

    _functions_ = {
 #QueryInterface -> riid:REFIID, ppvObject:**void
 "QueryInterface": ctypes.WINFUNCTYPE(HRESULT, REFIID, POINTER(PVOID))(0, "QueryInterface"),
 #AddRef -> 
 "AddRef": ctypes.WINFUNCTYPE(ULONG)(1, "AddRef"),
 #Release -> 
 "Release": ctypes.WINFUNCTYPE(ULONG)(2, "Release"),
 #GetError -> pContext:*BG_ERROR_CONTEXT, pCode:*HRESULT
 "GetError": ctypes.WINFUNCTYPE(HRESULT, POINTER(BG_ERROR_CONTEXT), POINTER(HRESULT))(3, "GetError"),
 #GetFile -> pVal:**IUnknown
 "GetFile": ctypes.WINFUNCTYPE(HRESULT, POINTER(PVOID))(4, "GetFile"),
 #GetErrorDescription -> LanguageId:DWORD, pErrorDescription:*LPWSTR
 "GetErrorDescription": ctypes.WINFUNCTYPE(HRESULT, DWORD, POINTER(LPWSTR))(5, "GetErrorDescription"),
 #GetErrorContextDescription -> LanguageId:DWORD, pContextDescription:*LPWSTR
 "GetErrorContextDescription": ctypes.WINFUNCTYPE(HRESULT, DWORD, POINTER(LPWSTR))(6, "GetErrorContextDescription"),
 #GetProtocol -> pProtocol:*LPWSTR
 "GetProtocol": ctypes.WINFUNCTYPE(HRESULT, POINTER(LPWSTR))(7, "GetProtocol"),
    }


class IBackgroundCopyFile(COMInterface):
    IID = generate_IID(0x01B7BD23, 0xFB88, 0x4A77, 0x84, 0x90, 0x58, 0x91, 0xD3, 0xE4, 0x65, 0x3A, name="IBackgroundCopyFile", strid="01B7BD23-FB88-4A77-8490-5891D3E4653A")

    _functions_ = {
 #QueryInterface -> riid:REFIID, ppvObject:**void
 "QueryInterface": ctypes.WINFUNCTYPE(HRESULT, REFIID, POINTER(PVOID))(0, "QueryInterface"),
 #AddRef -> 
 "AddRef": ctypes.WINFUNCTYPE(ULONG)(1, "AddRef"),
 #Release -> 
 "Release": ctypes.WINFUNCTYPE(ULONG)(2, "Release"),
 #GetRemoteName -> pVal:*LPWSTR
 "GetRemoteName": ctypes.WINFUNCTYPE(HRESULT, POINTER(LPWSTR))(3, "GetRemoteName"),
 #GetLocalName -> pVal:*LPWSTR
 "GetLocalName": ctypes.WINFUNCTYPE(HRESULT, POINTER(LPWSTR))(4, "GetLocalName"),
 #GetProgress -> pVal:*BG_FILE_PROGRESS
 "GetProgress": ctypes.WINFUNCTYPE(HRESULT, POINTER(BG_FILE_PROGRESS))(5, "GetProgress"),
    }


class IBackgroundCopyJob(COMInterface):
    IID = generate_IID(0x37668D37, 0x507E, 0x4160, 0x93, 0x16, 0x26, 0x30, 0x6D, 0x15, 0x0B, 0x12, name="IBackgroundCopyJob", strid="37668D37-507E-4160-9316-26306D150B12")

    _functions_ = {
 #QueryInterface -> riid:REFIID, ppvObject:**void
 "QueryInterface": ctypes.WINFUNCTYPE(HRESULT, REFIID, POINTER(PVOID))(0, "QueryInterface"),
 #AddRef -> 
 "AddRef": ctypes.WINFUNCTYPE(ULONG)(1, "AddRef"),
 #Release -> 
 "Release": ctypes.WINFUNCTYPE(ULONG)(2, "Release"),
 #AddFileSet -> cFileCount:ULONG, pFileSet:*BG_FILE_INFO
 "AddFileSet": ctypes.WINFUNCTYPE(HRESULT, ULONG, POINTER(BG_FILE_INFO))(3, "AddFileSet"),
 #AddFile -> RemoteUrl:LPCWSTR, LocalName:LPCWSTR
 "AddFile": ctypes.WINFUNCTYPE(HRESULT, LPCWSTR, LPCWSTR)(4, "AddFile"),
 #EnumFiles -> pEnum:**IEnumBackgroundCopyFiles
 "EnumFiles": ctypes.WINFUNCTYPE(HRESULT, POINTER(PVOID))(5, "EnumFiles"),
 #Suspend -> 
 "Suspend": ctypes.WINFUNCTYPE(HRESULT)(6, "Suspend"),
 #Resume -> 
 "Resume": ctypes.WINFUNCTYPE(HRESULT)(7, "Resume"),
 #Cancel -> 
 "Cancel": ctypes.WINFUNCTYPE(HRESULT)(8, "Cancel"),
 #Complete -> 
 "Complete": ctypes.WINFUNCTYPE(HRESULT)(9, "Complete"),
 #GetId -> pVal:*GUID
 "GetId": ctypes.WINFUNCTYPE(HRESULT, POINTER(GUID))(10, "GetId"),
 #GetType -> pVal:*BG_JOB_TYPE
 "GetType": ctypes.WINFUNCTYPE(HRESULT, POINTER(BG_JOB_TYPE))(11, "GetType"),
 #GetProgress -> pVal:*BG_JOB_PROGRESS
 "GetProgress": ctypes.WINFUNCTYPE(HRESULT, POINTER(BG_JOB_PROGRESS))(12, "GetProgress"),
 #GetTimes -> pVal:*BG_JOB_TIMES
 "GetTimes": ctypes.WINFUNCTYPE(HRESULT, POINTER(BG_JOB_TIMES))(13, "GetTimes"),
 #GetState -> pVal:*BG_JOB_STATE
 "GetState": ctypes.WINFUNCTYPE(HRESULT, POINTER(BG_JOB_STATE))(14, "GetState"),
 #GetError -> ppError:**IBackgroundCopyError
 "GetError": ctypes.WINFUNCTYPE(HRESULT, POINTER(PVOID))(15, "GetError"),
 #GetOwner -> pVal:*LPWSTR
 "GetOwner": ctypes.WINFUNCTYPE(HRESULT, POINTER(LPWSTR))(16, "GetOwner"),
 #SetDisplayName -> Val:LPCWSTR
 "SetDisplayName": ctypes.WINFUNCTYPE(HRESULT, LPCWSTR)(17, "SetDisplayName"),
 #GetDisplayName -> pVal:*LPWSTR
 "GetDisplayName": ctypes.WINFUNCTYPE(HRESULT, POINTER(LPWSTR))(18, "GetDisplayName"),
 #SetDescription -> Val:LPCWSTR
 "SetDescription": ctypes.WINFUNCTYPE(HRESULT, LPCWSTR)(19, "SetDescription"),
 #GetDescription -> pVal:*LPWSTR
 "GetDescription": ctypes.WINFUNCTYPE(HRESULT, POINTER(LPWSTR))(20, "GetDescription"),
 #SetPriority -> Val:BG_JOB_PRIORITY
 "SetPriority": ctypes.WINFUNCTYPE(HRESULT, BG_JOB_PRIORITY)(21, "SetPriority"),
 #GetPriority -> pVal:*BG_JOB_PRIORITY
 "GetPriority": ctypes.WINFUNCTYPE(HRESULT, POINTER(BG_JOB_PRIORITY))(22, "GetPriority"),
 #SetNotifyFlags -> Val:ULONG
 "SetNotifyFlags": ctypes.WINFUNCTYPE(HRESULT, ULONG)(23, "SetNotifyFlags"),
 #GetNotifyFlags -> pVal:*ULONG
 "GetNotifyFlags": ctypes.WINFUNCTYPE(HRESULT, POINTER(ULONG))(24, "GetNotifyFlags"),
 #SetNotifyInterface -> Val:*IUnknown
 "SetNotifyInterface": ctypes.WINFUNCTYPE(HRESULT, PVOID)(25, "SetNotifyInterface"),
 #GetNotifyInterface -> pVal:**IUnknown
 "GetNotifyInterface": ctypes.WINFUNCTYPE(HRESULT, POINTER(PVOID))(26, "GetNotifyInterface"),
 #SetMinimumRetryDelay -> Seconds:ULONG
 "SetMinimumRetryDelay": ctypes.WINFUNCTYPE(HRESULT, ULONG)(27, "SetMinimumRetryDelay"),
 #GetMinimumRetryDelay -> Seconds:*ULONG
 "GetMinimumRetryDelay": ctypes.WINFUNCTYPE(HRESULT, POINTER(ULONG))(28, "GetMinimumRetryDelay"),
 #SetNoProgressTimeout -> Seconds:ULONG
 "SetNoProgressTimeout": ctypes.WINFUNCTYPE(HRESULT, ULONG)(29, "SetNoProgressTimeout"),
 #GetNoProgressTimeout -> Seconds:*ULONG
 "GetNoProgressTimeout": ctypes.WINFUNCTYPE(HRESULT, POINTER(ULONG))(30, "GetNoProgressTimeout"),
 #GetErrorCount -> Errors:*ULONG
 "GetErrorCount": ctypes.WINFUNCTYPE(HRESULT, POINTER(ULONG))(31, "GetErrorCount"),
 #SetProxySettings -> ProxyUsage:BG_JOB_PROXY_USAGE, ProxyList:*WCHAR, ProxyBypassList:*WCHAR
 "SetProxySettings": ctypes.WINFUNCTYPE(HRESULT, BG_JOB_PROXY_USAGE, POINTER(WCHAR), POINTER(WCHAR))(32, "SetProxySettings"),
 #GetProxySettings -> pProxyUsage:*BG_JOB_PROXY_USAGE, pProxyList:*LPWSTR, pProxyBypassList:*LPWSTR
 "GetProxySettings": ctypes.WINFUNCTYPE(HRESULT, POINTER(BG_JOB_PROXY_USAGE), POINTER(LPWSTR), POINTER(LPWSTR))(33, "GetProxySettings"),
 #TakeOwnership -> 
 "TakeOwnership": ctypes.WINFUNCTYPE(HRESULT)(34, "TakeOwnership"),
    }


class IBackgroundCopyManager(COMInterface):
    IID = generate_IID(0x5CE34C0D, 0x0DC9, 0x4C1F, 0x89, 0x7C, 0xDA, 0xA1, 0xB7, 0x8C, 0xEE, 0x7C, name="IBackgroundCopyManager", strid="5CE34C0D-0DC9-4C1F-897C-DAA1B78CEE7C")

    _functions_ = {
 #QueryInterface -> riid:REFIID, ppvObject:**void
 "QueryInterface": ctypes.WINFUNCTYPE(HRESULT, REFIID, POINTER(PVOID))(0, "QueryInterface"),
 #AddRef -> 
 "AddRef": ctypes.WINFUNCTYPE(ULONG)(1, "AddRef"),
 #Release -> 
 "Release": ctypes.WINFUNCTYPE(ULONG)(2, "Release"),
 #CreateJob -> DisplayName:LPCWSTR, Type:BG_JOB_TYPE, pJobId:*GUID, ppJob:**IBackgroundCopyJob
 "CreateJob": ctypes.WINFUNCTYPE(HRESULT, LPCWSTR, BG_JOB_TYPE, POINTER(GUID), POINTER(PVOID))(3, "CreateJob"),
 #GetJob -> jobID:REFGUID, ppJob:**IBackgroundCopyJob
 "GetJob": ctypes.WINFUNCTYPE(HRESULT, REFGUID, POINTER(PVOID))(4, "GetJob"),
 #EnumJobs -> dwFlags:DWORD, ppEnum:**IEnumWbemClassObject
 "EnumJobs": ctypes.WINFUNCTYPE(HRESULT, DWORD, POINTER(PVOID))(5, "EnumJobs"),
 #GetErrorDescription -> hResult:HRESULT, LanguageId:DWORD, pErrorDescription:*LPWSTR
 "GetErrorDescription": ctypes.WINFUNCTYPE(HRESULT, HRESULT, DWORD, POINTER(LPWSTR))(6, "GetErrorDescription"),
    }


class IDispatch(COMInterface):
    IID = generate_IID(0x00020400, 0x0000, 0x0000, 0xC0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x46, name="IDispatch", strid="00020400-0000-0000-C000-000000000046")

    _functions_ = {
 #QueryInterface -> riid:REFIID, ppvObject:**void
 "QueryInterface": ctypes.WINFUNCTYPE(HRESULT, REFIID, POINTER(PVOID))(0, "QueryInterface"),
 #AddRef -> 
 "AddRef": ctypes.WINFUNCTYPE(ULONG)(1, "AddRef"),
 #Release -> 
 "Release": ctypes.WINFUNCTYPE(ULONG)(2, "Release"),
 #GetTypeInfoCount -> pctinfo:*UINT
 "GetTypeInfoCount": ctypes.WINFUNCTYPE(HRESULT, POINTER(UINT))(3, "GetTypeInfoCount"),
 #GetTypeInfo -> iTInfo:UINT, lcid:LCID, ppTInfo:**ITypeInfo
 "GetTypeInfo": ctypes.WINFUNCTYPE(HRESULT, UINT, LCID, POINTER(PVOID))(4, "GetTypeInfo"),
 #GetIDsOfNames -> riid:REFIID, rgszNames:*LPOLESTR, cNames:UINT, lcid:LCID, rgDispId:*DISPID
 "GetIDsOfNames": ctypes.WINFUNCTYPE(HRESULT, REFIID, POINTER(LPOLESTR), UINT, LCID, POINTER(DISPID))(5, "GetIDsOfNames"),
 #Invoke -> dispIdMember:DISPID, riid:REFIID, lcid:LCID, wFlags:WORD, pDispParams:*DISPPARAMS, pVarResult:*VARIANT, pExcepInfo:*EXCEPINFO, puArgErr:*UINT
 "Invoke": ctypes.WINFUNCTYPE(HRESULT, DISPID, REFIID, LCID, WORD, POINTER(DISPPARAMS), POINTER(VARIANT), POINTER(EXCEPINFO), POINTER(UINT))(6, "Invoke"),
    }


class IEnumBackgroundCopyFiles(COMInterface):
    IID = generate_IID(0xCA51E165, 0xC365, 0x424C, 0x8D, 0x41, 0x24, 0xAA, 0xA4, 0xFF, 0x3C, 0x40, name="IEnumBackgroundCopyFiles", strid="CA51E165-C365-424C-8D41-24AAA4FF3C40")

    _functions_ = {
 #QueryInterface -> riid:REFIID, ppvObject:**void
 "QueryInterface": ctypes.WINFUNCTYPE(HRESULT, REFIID, POINTER(PVOID))(0, "QueryInterface"),
 #AddRef -> 
 "AddRef": ctypes.WINFUNCTYPE(ULONG)(1, "AddRef"),
 #Release -> 
 "Release": ctypes.WINFUNCTYPE(ULONG)(2, "Release"),
 #Next -> celt:ULONG, rgelt:**IBackgroundCopyJob, pceltFetched:*ULONG
 "Next": ctypes.WINFUNCTYPE(HRESULT, ULONG, POINTER(PVOID), POINTER(ULONG))(3, "Next"),
 #Skip -> celt:ULONG
 "Skip": ctypes.WINFUNCTYPE(HRESULT, ULONG)(4, "Skip"),
 #Reset -> 
 "Reset": ctypes.WINFUNCTYPE(HRESULT)(5, "Reset"),
 #Clone -> ppenum:**IEnumBackgroundCopyJobs
 "Clone": ctypes.WINFUNCTYPE(HRESULT, POINTER(PVOID))(6, "Clone"),
 #GetCount -> puCount:*ULONG
 "GetCount": ctypes.WINFUNCTYPE(HRESULT, POINTER(ULONG))(7, "GetCount"),
    }


class IEnumBackgroundCopyJobs(COMInterface):
    IID = generate_IID(0x1AF4F612, 0x3B71, 0x466F, 0x8F, 0x58, 0x7B, 0x6F, 0x73, 0xAC, 0x57, 0xAD, name="IEnumBackgroundCopyJobs", strid="1AF4F612-3B71-466F-8F58-7B6F73AC57AD")

    _functions_ = {
 #QueryInterface -> riid:REFIID, ppvObject:**void
 "QueryInterface": ctypes.WINFUNCTYPE(HRESULT, REFIID, POINTER(PVOID))(0, "QueryInterface"),
 #AddRef -> 
 "AddRef": ctypes.WINFUNCTYPE(ULONG)(1, "AddRef"),
 #Release -> 
 "Release": ctypes.WINFUNCTYPE(ULONG)(2, "Release"),
 #Next -> celt:ULONG, rgelt:**IBackgroundCopyJob, pceltFetched:*ULONG
 "Next": ctypes.WINFUNCTYPE(HRESULT, ULONG, POINTER(PVOID), POINTER(ULONG))(3, "Next"),
 #Skip -> celt:ULONG
 "Skip": ctypes.WINFUNCTYPE(HRESULT, ULONG)(4, "Skip"),
 #Reset -> 
 "Reset": ctypes.WINFUNCTYPE(HRESULT)(5, "Reset"),
 #Clone -> ppenum:**IEnumBackgroundCopyJobs
 "Clone": ctypes.WINFUNCTYPE(HRESULT, POINTER(PVOID))(6, "Clone"),
 #GetCount -> puCount:*ULONG
 "GetCount": ctypes.WINFUNCTYPE(HRESULT, POINTER(ULONG))(7, "GetCount"),
    }


class IEnumVARIANT(COMInterface):
    IID = generate_IID(0x00020404, 0x0000, 0x0000, 0xC0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x46, name="IEnumVARIANT", strid="00020404-0000-0000-C000-000000000046")

    _functions_ = {
 #QueryInterface -> riid:REFIID, ppvObject:**void
 "QueryInterface": ctypes.WINFUNCTYPE(HRESULT, REFIID, POINTER(PVOID))(0, "QueryInterface"),
 #AddRef -> 
 "AddRef": ctypes.WINFUNCTYPE(ULONG)(1, "AddRef"),
 #Release -> 
 "Release": ctypes.WINFUNCTYPE(ULONG)(2, "Release"),
 #Next -> celt:ULONG, rgVar:*VARIANT, pCeltFetched:*ULONG
 "Next": ctypes.WINFUNCTYPE(HRESULT, ULONG, POINTER(VARIANT), POINTER(ULONG))(3, "Next"),
 #Skip -> celt:ULONG
 "Skip": ctypes.WINFUNCTYPE(HRESULT, ULONG)(4, "Skip"),
 #Reset -> 
 "Reset": ctypes.WINFUNCTYPE(HRESULT)(5, "Reset"),
 #Clone -> ppEnum:**IEnumWbemClassObject
 "Clone": ctypes.WINFUNCTYPE(HRESULT, POINTER(PVOID))(6, "Clone"),
    }


class IEnumWbemClassObject(COMInterface):
    IID = generate_IID(0x027947E1, 0xD731, 0x11CE, 0xA3, 0x57, 0x00, 0x00, 0x00, 0x00, 0x00, 0x01, name="IEnumWbemClassObject", strid="027947E1-D731-11CE-A357-000000000001")

    _functions_ = {
 #QueryInterface -> riid:REFIID, ppvObject:**void
 "QueryInterface": ctypes.WINFUNCTYPE(HRESULT, REFIID, POINTER(PVOID))(0, "QueryInterface"),
 #AddRef -> 
 "AddRef": ctypes.WINFUNCTYPE(ULONG)(1, "AddRef"),
 #Release -> 
 "Release": ctypes.WINFUNCTYPE(ULONG)(2, "Release"),
 #Reset -> 
 "Reset": ctypes.WINFUNCTYPE(HRESULT)(3, "Reset"),
 #Next -> lTimeout:LONG, uCount:ULONG, apObjects:**IWbemClassObject, puReturned:*ULONG
 "Next": ctypes.WINFUNCTYPE(HRESULT, LONG, ULONG, POINTER(PVOID), POINTER(ULONG))(4, "Next"),
 #NextAsync -> uCount:ULONG, pSink:*IWbemObjectSink
 "NextAsync": ctypes.WINFUNCTYPE(HRESULT, ULONG, PVOID)(5, "NextAsync"),
 #Clone -> ppEnum:**IEnumWbemClassObject
 "Clone": ctypes.WINFUNCTYPE(HRESULT, POINTER(PVOID))(6, "Clone"),
 #Skip -> lTimeout:LONG, nCount:ULONG
 "Skip": ctypes.WINFUNCTYPE(HRESULT, LONG, ULONG)(7, "Skip"),
    }


class INetFwPolicy2(COMInterface):
    IID = generate_IID(0x98325047, 0xC671, 0x4174, 0x8D, 0x81, 0xDE, 0xFC, 0xD3, 0xF0, 0x31, 0x86, name="INetFwPolicy2", strid="98325047-C671-4174-8D81-DEFCD3F03186")

    _functions_ = {
 #QueryInterface -> riid:REFIID, ppvObject:**void
 "QueryInterface": ctypes.WINFUNCTYPE(HRESULT, REFIID, POINTER(PVOID))(0, "QueryInterface"),
 #AddRef -> 
 "AddRef": ctypes.WINFUNCTYPE(ULONG)(1, "AddRef"),
 #Release -> 
 "Release": ctypes.WINFUNCTYPE(ULONG)(2, "Release"),
 #GetTypeInfoCount -> pctinfo:*UINT
 "GetTypeInfoCount": ctypes.WINFUNCTYPE(HRESULT, POINTER(UINT))(3, "GetTypeInfoCount"),
 #GetTypeInfo -> iTInfo:UINT, lcid:LCID, ppTInfo:**ITypeInfo
 "GetTypeInfo": ctypes.WINFUNCTYPE(HRESULT, UINT, LCID, POINTER(PVOID))(4, "GetTypeInfo"),
 #GetIDsOfNames -> riid:REFIID, rgszNames:*LPOLESTR, cNames:UINT, lcid:LCID, rgDispId:*DISPID
 "GetIDsOfNames": ctypes.WINFUNCTYPE(HRESULT, REFIID, POINTER(LPOLESTR), UINT, LCID, POINTER(DISPID))(5, "GetIDsOfNames"),
 #Invoke -> dispIdMember:DISPID, riid:REFIID, lcid:LCID, wFlags:WORD, pDispParams:*DISPPARAMS, pVarResult:*VARIANT, pExcepInfo:*EXCEPINFO, puArgErr:*UINT
 "Invoke": ctypes.WINFUNCTYPE(HRESULT, DISPID, REFIID, LCID, WORD, POINTER(DISPPARAMS), POINTER(VARIANT), POINTER(EXCEPINFO), POINTER(UINT))(6, "Invoke"),
 #get_CurrentProfileTypes -> profileTypesBitmask:*LONG
 "get_CurrentProfileTypes": ctypes.WINFUNCTYPE(HRESULT, POINTER(LONG))(7, "get_CurrentProfileTypes"),
 #get_FirewallEnabled -> profileType:NET_FW_PROFILE_TYPE2, enabled:*VARIANT_BOOL
 "get_FirewallEnabled": ctypes.WINFUNCTYPE(HRESULT, NET_FW_PROFILE_TYPE2, POINTER(VARIANT_BOOL))(8, "get_FirewallEnabled"),
 #put_FirewallEnabled -> profileType:NET_FW_PROFILE_TYPE2, enabled:VARIANT_BOOL
 "put_FirewallEnabled": ctypes.WINFUNCTYPE(HRESULT, NET_FW_PROFILE_TYPE2, VARIANT_BOOL)(9, "put_FirewallEnabled"),
 #get_ExcludedInterfaces -> profileType:NET_FW_PROFILE_TYPE2, interfaces:*VARIANT
 "get_ExcludedInterfaces": ctypes.WINFUNCTYPE(HRESULT, NET_FW_PROFILE_TYPE2, POINTER(VARIANT))(10, "get_ExcludedInterfaces"),
 #put_ExcludedInterfaces -> profileType:NET_FW_PROFILE_TYPE2, interfaces:VARIANT
 "put_ExcludedInterfaces": ctypes.WINFUNCTYPE(HRESULT, NET_FW_PROFILE_TYPE2, VARIANT)(11, "put_ExcludedInterfaces"),
 #get_BlockAllInboundTraffic -> profileType:NET_FW_PROFILE_TYPE2, Block:*VARIANT_BOOL
 "get_BlockAllInboundTraffic": ctypes.WINFUNCTYPE(HRESULT, NET_FW_PROFILE_TYPE2, POINTER(VARIANT_BOOL))(12, "get_BlockAllInboundTraffic"),
 #put_BlockAllInboundTraffic -> profileType:NET_FW_PROFILE_TYPE2, Block:VARIANT_BOOL
 "put_BlockAllInboundTraffic": ctypes.WINFUNCTYPE(HRESULT, NET_FW_PROFILE_TYPE2, VARIANT_BOOL)(13, "put_BlockAllInboundTraffic"),
 #get_NotificationsDisabled -> profileType:NET_FW_PROFILE_TYPE2, disabled:*VARIANT_BOOL
 "get_NotificationsDisabled": ctypes.WINFUNCTYPE(HRESULT, NET_FW_PROFILE_TYPE2, POINTER(VARIANT_BOOL))(14, "get_NotificationsDisabled"),
 #put_NotificationsDisabled -> profileType:NET_FW_PROFILE_TYPE2, disabled:VARIANT_BOOL
 "put_NotificationsDisabled": ctypes.WINFUNCTYPE(HRESULT, NET_FW_PROFILE_TYPE2, VARIANT_BOOL)(15, "put_NotificationsDisabled"),
 #get_UnicastResponsesToMulticastBroadcastDisabled -> profileType:NET_FW_PROFILE_TYPE2, disabled:*VARIANT_BOOL
 "get_UnicastResponsesToMulticastBroadcastDisabled": ctypes.WINFUNCTYPE(HRESULT, NET_FW_PROFILE_TYPE2, POINTER(VARIANT_BOOL))(16, "get_UnicastResponsesToMulticastBroadcastDisabled"),
 #put_UnicastResponsesToMulticastBroadcastDisabled -> profileType:NET_FW_PROFILE_TYPE2, disabled:VARIANT_BOOL
 "put_UnicastResponsesToMulticastBroadcastDisabled": ctypes.WINFUNCTYPE(HRESULT, NET_FW_PROFILE_TYPE2, VARIANT_BOOL)(17, "put_UnicastResponsesToMulticastBroadcastDisabled"),
 #get_Rules -> rules:**INetFwRules
 "get_Rules": ctypes.WINFUNCTYPE(HRESULT, POINTER(PVOID))(18, "get_Rules"),
 #get_ServiceRestriction -> ServiceRestriction:**INetFwServiceRestriction
 "get_ServiceRestriction": ctypes.WINFUNCTYPE(HRESULT, POINTER(PVOID))(19, "get_ServiceRestriction"),
 #EnableRuleGroup -> profileTypesBitmask:LONG, group:BSTR, enable:VARIANT_BOOL
 "EnableRuleGroup": ctypes.WINFUNCTYPE(HRESULT, LONG, BSTR, VARIANT_BOOL)(20, "EnableRuleGroup"),
 #IsRuleGroupEnabled -> profileTypesBitmask:LONG, group:BSTR, enabled:*VARIANT_BOOL
 "IsRuleGroupEnabled": ctypes.WINFUNCTYPE(HRESULT, LONG, BSTR, POINTER(VARIANT_BOOL))(21, "IsRuleGroupEnabled"),
 #RestoreLocalFirewallDefaults -> 
 "RestoreLocalFirewallDefaults": ctypes.WINFUNCTYPE(HRESULT)(22, "RestoreLocalFirewallDefaults"),
 #get_DefaultInboundAction -> profileType:NET_FW_PROFILE_TYPE2, action:*NET_FW_ACTION
 "get_DefaultInboundAction": ctypes.WINFUNCTYPE(HRESULT, NET_FW_PROFILE_TYPE2, POINTER(NET_FW_ACTION))(23, "get_DefaultInboundAction"),
 #put_DefaultInboundAction -> profileType:NET_FW_PROFILE_TYPE2, action:NET_FW_ACTION
 "put_DefaultInboundAction": ctypes.WINFUNCTYPE(HRESULT, NET_FW_PROFILE_TYPE2, NET_FW_ACTION)(24, "put_DefaultInboundAction"),
 #get_DefaultOutboundAction -> profileType:NET_FW_PROFILE_TYPE2, action:*NET_FW_ACTION
 "get_DefaultOutboundAction": ctypes.WINFUNCTYPE(HRESULT, NET_FW_PROFILE_TYPE2, POINTER(NET_FW_ACTION))(25, "get_DefaultOutboundAction"),
 #put_DefaultOutboundAction -> profileType:NET_FW_PROFILE_TYPE2, action:NET_FW_ACTION
 "put_DefaultOutboundAction": ctypes.WINFUNCTYPE(HRESULT, NET_FW_PROFILE_TYPE2, NET_FW_ACTION)(26, "put_DefaultOutboundAction"),
 #get_IsRuleGroupCurrentlyEnabled -> group:BSTR, enabled:*VARIANT_BOOL
 "get_IsRuleGroupCurrentlyEnabled": ctypes.WINFUNCTYPE(HRESULT, BSTR, POINTER(VARIANT_BOOL))(27, "get_IsRuleGroupCurrentlyEnabled"),
 #get_LocalPolicyModifyState -> modifyState:*NET_FW_MODIFY_STATE
 "get_LocalPolicyModifyState": ctypes.WINFUNCTYPE(HRESULT, POINTER(NET_FW_MODIFY_STATE))(28, "get_LocalPolicyModifyState"),
    }


class INetFwRules(COMInterface):
    IID = generate_IID(0x9C4C6277, 0x5027, 0x441E, 0xAF, 0xAE, 0xCA, 0x1F, 0x54, 0x2D, 0xA0, 0x09, name="INetFwRules", strid="9C4C6277-5027-441E-AFAE-CA1F542DA009")

    _functions_ = {
 #QueryInterface -> riid:REFIID, ppvObject:**void
 "QueryInterface": ctypes.WINFUNCTYPE(HRESULT, REFIID, POINTER(PVOID))(0, "QueryInterface"),
 #AddRef -> 
 "AddRef": ctypes.WINFUNCTYPE(ULONG)(1, "AddRef"),
 #Release -> 
 "Release": ctypes.WINFUNCTYPE(ULONG)(2, "Release"),
 #GetTypeInfoCount -> pctinfo:*UINT
 "GetTypeInfoCount": ctypes.WINFUNCTYPE(HRESULT, POINTER(UINT))(3, "GetTypeInfoCount"),
 #GetTypeInfo -> iTInfo:UINT, lcid:LCID, ppTInfo:**ITypeInfo
 "GetTypeInfo": ctypes.WINFUNCTYPE(HRESULT, UINT, LCID, POINTER(PVOID))(4, "GetTypeInfo"),
 #GetIDsOfNames -> riid:REFIID, rgszNames:*LPOLESTR, cNames:UINT, lcid:LCID, rgDispId:*DISPID
 "GetIDsOfNames": ctypes.WINFUNCTYPE(HRESULT, REFIID, POINTER(LPOLESTR), UINT, LCID, POINTER(DISPID))(5, "GetIDsOfNames"),
 #Invoke -> dispIdMember:DISPID, riid:REFIID, lcid:LCID, wFlags:WORD, pDispParams:*DISPPARAMS, pVarResult:*VARIANT, pExcepInfo:*EXCEPINFO, puArgErr:*UINT
 "Invoke": ctypes.WINFUNCTYPE(HRESULT, DISPID, REFIID, LCID, WORD, POINTER(DISPPARAMS), POINTER(VARIANT), POINTER(EXCEPINFO), POINTER(UINT))(6, "Invoke"),
 #get_Count -> count:*LONG
 "get_Count": ctypes.WINFUNCTYPE(HRESULT, POINTER(LONG))(7, "get_Count"),
 #Add -> rule:*INetFwRule
 "Add": ctypes.WINFUNCTYPE(HRESULT, PVOID)(8, "Add"),
 #Remove -> name:BSTR
 "Remove": ctypes.WINFUNCTYPE(HRESULT, BSTR)(9, "Remove"),
 #Item -> name:BSTR, rule:**INetFwRule
 "Item": ctypes.WINFUNCTYPE(HRESULT, BSTR, POINTER(PVOID))(10, "Item"),
 #get__NewEnum -> newEnum:**IUnknown
 "get__NewEnum": ctypes.WINFUNCTYPE(HRESULT, POINTER(PVOID))(11, "get__NewEnum"),
    }


class INetFwRule(COMInterface):
    IID = generate_IID(0xAF230D27, 0xBABA, 0x4E42, 0xAC, 0xED, 0xF5, 0x24, 0xF2, 0x2C, 0xFC, 0xE2, name="INetFwRule", strid="AF230D27-BABA-4E42-ACED-F524F22CFCE2")

    _functions_ = {
 #QueryInterface -> riid:REFIID, ppvObject:**void
 "QueryInterface": ctypes.WINFUNCTYPE(HRESULT, REFIID, POINTER(PVOID))(0, "QueryInterface"),
 #AddRef -> 
 "AddRef": ctypes.WINFUNCTYPE(ULONG)(1, "AddRef"),
 #Release -> 
 "Release": ctypes.WINFUNCTYPE(ULONG)(2, "Release"),
 #GetTypeInfoCount -> pctinfo:*UINT
 "GetTypeInfoCount": ctypes.WINFUNCTYPE(HRESULT, POINTER(UINT))(3, "GetTypeInfoCount"),
 #GetTypeInfo -> iTInfo:UINT, lcid:LCID, ppTInfo:**ITypeInfo
 "GetTypeInfo": ctypes.WINFUNCTYPE(HRESULT, UINT, LCID, POINTER(PVOID))(4, "GetTypeInfo"),
 #GetIDsOfNames -> riid:REFIID, rgszNames:*LPOLESTR, cNames:UINT, lcid:LCID, rgDispId:*DISPID
 "GetIDsOfNames": ctypes.WINFUNCTYPE(HRESULT, REFIID, POINTER(LPOLESTR), UINT, LCID, POINTER(DISPID))(5, "GetIDsOfNames"),
 #Invoke -> dispIdMember:DISPID, riid:REFIID, lcid:LCID, wFlags:WORD, pDispParams:*DISPPARAMS, pVarResult:*VARIANT, pExcepInfo:*EXCEPINFO, puArgErr:*UINT
 "Invoke": ctypes.WINFUNCTYPE(HRESULT, DISPID, REFIID, LCID, WORD, POINTER(DISPPARAMS), POINTER(VARIANT), POINTER(EXCEPINFO), POINTER(UINT))(6, "Invoke"),
 #get_Name -> name:*BSTR
 "get_Name": ctypes.WINFUNCTYPE(HRESULT, POINTER(BSTR))(7, "get_Name"),
 #put_Name -> name:BSTR
 "put_Name": ctypes.WINFUNCTYPE(HRESULT, BSTR)(8, "put_Name"),
 #get_Description -> desc:*BSTR
 "get_Description": ctypes.WINFUNCTYPE(HRESULT, POINTER(BSTR))(9, "get_Description"),
 #put_Description -> desc:BSTR
 "put_Description": ctypes.WINFUNCTYPE(HRESULT, BSTR)(10, "put_Description"),
 #get_ApplicationName -> imageFileName:*BSTR
 "get_ApplicationName": ctypes.WINFUNCTYPE(HRESULT, POINTER(BSTR))(11, "get_ApplicationName"),
 #put_ApplicationName -> imageFileName:BSTR
 "put_ApplicationName": ctypes.WINFUNCTYPE(HRESULT, BSTR)(12, "put_ApplicationName"),
 #get_ServiceName -> serviceName:*BSTR
 "get_ServiceName": ctypes.WINFUNCTYPE(HRESULT, POINTER(BSTR))(13, "get_ServiceName"),
 #put_ServiceName -> serviceName:BSTR
 "put_ServiceName": ctypes.WINFUNCTYPE(HRESULT, BSTR)(14, "put_ServiceName"),
 #get_Protocol -> protocol:*LONG
 "get_Protocol": ctypes.WINFUNCTYPE(HRESULT, POINTER(LONG))(15, "get_Protocol"),
 #put_Protocol -> protocol:LONG
 "put_Protocol": ctypes.WINFUNCTYPE(HRESULT, LONG)(16, "put_Protocol"),
 #get_LocalPorts -> portNumbers:*BSTR
 "get_LocalPorts": ctypes.WINFUNCTYPE(HRESULT, POINTER(BSTR))(17, "get_LocalPorts"),
 #put_LocalPorts -> portNumbers:BSTR
 "put_LocalPorts": ctypes.WINFUNCTYPE(HRESULT, BSTR)(18, "put_LocalPorts"),
 #get_RemotePorts -> portNumbers:*BSTR
 "get_RemotePorts": ctypes.WINFUNCTYPE(HRESULT, POINTER(BSTR))(19, "get_RemotePorts"),
 #put_RemotePorts -> portNumbers:BSTR
 "put_RemotePorts": ctypes.WINFUNCTYPE(HRESULT, BSTR)(20, "put_RemotePorts"),
 #get_LocalAddresses -> localAddrs:*BSTR
 "get_LocalAddresses": ctypes.WINFUNCTYPE(HRESULT, POINTER(BSTR))(21, "get_LocalAddresses"),
 #put_LocalAddresses -> localAddrs:BSTR
 "put_LocalAddresses": ctypes.WINFUNCTYPE(HRESULT, BSTR)(22, "put_LocalAddresses"),
 #get_RemoteAddresses -> remoteAddrs:*BSTR
 "get_RemoteAddresses": ctypes.WINFUNCTYPE(HRESULT, POINTER(BSTR))(23, "get_RemoteAddresses"),
 #put_RemoteAddresses -> remoteAddrs:BSTR
 "put_RemoteAddresses": ctypes.WINFUNCTYPE(HRESULT, BSTR)(24, "put_RemoteAddresses"),
 #get_IcmpTypesAndCodes -> icmpTypesAndCodes:*BSTR
 "get_IcmpTypesAndCodes": ctypes.WINFUNCTYPE(HRESULT, POINTER(BSTR))(25, "get_IcmpTypesAndCodes"),
 #put_IcmpTypesAndCodes -> icmpTypesAndCodes:BSTR
 "put_IcmpTypesAndCodes": ctypes.WINFUNCTYPE(HRESULT, BSTR)(26, "put_IcmpTypesAndCodes"),
 #get_Direction -> dir:*NET_FW_RULE_DIRECTION
 "get_Direction": ctypes.WINFUNCTYPE(HRESULT, POINTER(NET_FW_RULE_DIRECTION))(27, "get_Direction"),
 #put_Direction -> dir:NET_FW_RULE_DIRECTION
 "put_Direction": ctypes.WINFUNCTYPE(HRESULT, NET_FW_RULE_DIRECTION)(28, "put_Direction"),
 #get_Interfaces -> interfaces:*VARIANT
 "get_Interfaces": ctypes.WINFUNCTYPE(HRESULT, POINTER(VARIANT))(29, "get_Interfaces"),
 #put_Interfaces -> interfaces:VARIANT
 "put_Interfaces": ctypes.WINFUNCTYPE(HRESULT, VARIANT)(30, "put_Interfaces"),
 #get_InterfaceTypes -> interfaceTypes:*BSTR
 "get_InterfaceTypes": ctypes.WINFUNCTYPE(HRESULT, POINTER(BSTR))(31, "get_InterfaceTypes"),
 #put_InterfaceTypes -> interfaceTypes:BSTR
 "put_InterfaceTypes": ctypes.WINFUNCTYPE(HRESULT, BSTR)(32, "put_InterfaceTypes"),
 #get_Enabled -> enabled:*VARIANT_BOOL
 "get_Enabled": ctypes.WINFUNCTYPE(HRESULT, POINTER(VARIANT_BOOL))(33, "get_Enabled"),
 #put_Enabled -> enabled:VARIANT_BOOL
 "put_Enabled": ctypes.WINFUNCTYPE(HRESULT, VARIANT_BOOL)(34, "put_Enabled"),
 #get_Grouping -> context:*BSTR
 "get_Grouping": ctypes.WINFUNCTYPE(HRESULT, POINTER(BSTR))(35, "get_Grouping"),
 #put_Grouping -> context:BSTR
 "put_Grouping": ctypes.WINFUNCTYPE(HRESULT, BSTR)(36, "put_Grouping"),
 #get_Profiles -> profileTypesBitmask:*LONG
 "get_Profiles": ctypes.WINFUNCTYPE(HRESULT, POINTER(LONG))(37, "get_Profiles"),
 #put_Profiles -> profileTypesBitmask:LONG
 "put_Profiles": ctypes.WINFUNCTYPE(HRESULT, LONG)(38, "put_Profiles"),
 #get_EdgeTraversal -> enabled:*VARIANT_BOOL
 "get_EdgeTraversal": ctypes.WINFUNCTYPE(HRESULT, POINTER(VARIANT_BOOL))(39, "get_EdgeTraversal"),
 #put_EdgeTraversal -> enabled:VARIANT_BOOL
 "put_EdgeTraversal": ctypes.WINFUNCTYPE(HRESULT, VARIANT_BOOL)(40, "put_EdgeTraversal"),
 #get_Action -> action:*NET_FW_ACTION
 "get_Action": ctypes.WINFUNCTYPE(HRESULT, POINTER(NET_FW_ACTION))(41, "get_Action"),
 #put_Action -> action:NET_FW_ACTION
 "put_Action": ctypes.WINFUNCTYPE(HRESULT, NET_FW_ACTION)(42, "put_Action"),
    }


class INetFwServiceRestriction(COMInterface):
    IID = generate_IID(0x8267BBE3, 0xF890, 0x491C, 0xB7, 0xB6, 0x2D, 0xB1, 0xEF, 0x0E, 0x5D, 0x2B, name="INetFwServiceRestriction", strid="8267BBE3-F890-491C-B7B6-2DB1EF0E5D2B")

    _functions_ = {
 #QueryInterface -> riid:REFIID, ppvObject:**void
 "QueryInterface": ctypes.WINFUNCTYPE(HRESULT, REFIID, POINTER(PVOID))(0, "QueryInterface"),
 #AddRef -> 
 "AddRef": ctypes.WINFUNCTYPE(ULONG)(1, "AddRef"),
 #Release -> 
 "Release": ctypes.WINFUNCTYPE(ULONG)(2, "Release"),
 #GetTypeInfoCount -> pctinfo:*UINT
 "GetTypeInfoCount": ctypes.WINFUNCTYPE(HRESULT, POINTER(UINT))(3, "GetTypeInfoCount"),
 #GetTypeInfo -> iTInfo:UINT, lcid:LCID, ppTInfo:**ITypeInfo
 "GetTypeInfo": ctypes.WINFUNCTYPE(HRESULT, UINT, LCID, POINTER(PVOID))(4, "GetTypeInfo"),
 #GetIDsOfNames -> riid:REFIID, rgszNames:*LPOLESTR, cNames:UINT, lcid:LCID, rgDispId:*DISPID
 "GetIDsOfNames": ctypes.WINFUNCTYPE(HRESULT, REFIID, POINTER(LPOLESTR), UINT, LCID, POINTER(DISPID))(5, "GetIDsOfNames"),
 #Invoke -> dispIdMember:DISPID, riid:REFIID, lcid:LCID, wFlags:WORD, pDispParams:*DISPPARAMS, pVarResult:*VARIANT, pExcepInfo:*EXCEPINFO, puArgErr:*UINT
 "Invoke": ctypes.WINFUNCTYPE(HRESULT, DISPID, REFIID, LCID, WORD, POINTER(DISPPARAMS), POINTER(VARIANT), POINTER(EXCEPINFO), POINTER(UINT))(6, "Invoke"),
 #RestrictService -> serviceName:BSTR, appName:BSTR, restrictService:VARIANT_BOOL, serviceSidRestricted:VARIANT_BOOL
 "RestrictService": ctypes.WINFUNCTYPE(HRESULT, BSTR, BSTR, VARIANT_BOOL, VARIANT_BOOL)(7, "RestrictService"),
 #ServiceRestricted -> serviceName:BSTR, appName:BSTR, serviceRestricted:*VARIANT_BOOL
 "ServiceRestricted": ctypes.WINFUNCTYPE(HRESULT, BSTR, BSTR, POINTER(VARIANT_BOOL))(8, "ServiceRestricted"),
 #get_Rules -> rules:**INetFwRules
 "get_Rules": ctypes.WINFUNCTYPE(HRESULT, POINTER(PVOID))(9, "get_Rules"),
    }


class IUnknown(COMInterface):
    IID = generate_IID(0x00000000, 0x0000, 0x0000, 0xC0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x46, name="IUnknown", strid="00000000-0000-0000-C000-000000000046")

    _functions_ = {
 #QueryInterface -> riid:REFIID, ppvObject:**void
 "QueryInterface": ctypes.WINFUNCTYPE(HRESULT, REFIID, POINTER(PVOID))(0, "QueryInterface"),
 #AddRef -> 
 "AddRef": ctypes.WINFUNCTYPE(ULONG)(1, "AddRef"),
 #Release -> 
 "Release": ctypes.WINFUNCTYPE(ULONG)(2, "Release"),
    }


class IWbemCallResult(COMInterface):
    IID = generate_IID(0x44ACA675, 0xE8FC, 0x11D0, 0xA0, 0x7C, 0x00, 0xC0, 0x4F, 0xB6, 0x88, 0x20, name="IWbemCallResult", strid="44ACA675-E8FC-11D0-A07C-00C04FB68820")

    _functions_ = {
 #QueryInterface -> riid:REFIID, ppvObject:**void
 "QueryInterface": ctypes.WINFUNCTYPE(HRESULT, REFIID, POINTER(PVOID))(0, "QueryInterface"),
 #AddRef -> 
 "AddRef": ctypes.WINFUNCTYPE(ULONG)(1, "AddRef"),
 #Release -> 
 "Release": ctypes.WINFUNCTYPE(ULONG)(2, "Release"),
 #GetResultObject -> lTimeout:LONG, ppResultObject:**IWbemClassObject
 "GetResultObject": ctypes.WINFUNCTYPE(HRESULT, LONG, POINTER(PVOID))(3, "GetResultObject"),
 #GetResultString -> lTimeout:LONG, pstrResultString:*BSTR
 "GetResultString": ctypes.WINFUNCTYPE(HRESULT, LONG, POINTER(BSTR))(4, "GetResultString"),
 #GetResultServices -> lTimeout:LONG, ppServices:**IWbemServices
 "GetResultServices": ctypes.WINFUNCTYPE(HRESULT, LONG, POINTER(PVOID))(5, "GetResultServices"),
 #GetCallStatus -> lTimeout:LONG, plStatus:*LONG
 "GetCallStatus": ctypes.WINFUNCTYPE(HRESULT, LONG, POINTER(LONG))(6, "GetCallStatus"),
    }


class IWbemClassObject(COMInterface):
    IID = generate_IID(0xDC12A681, 0x737F, 0x11CF, 0x88, 0x4D, 0x00, 0xAA, 0x00, 0x4B, 0x2E, 0x24, name="IWbemClassObject", strid="DC12A681-737F-11CF-884D-00AA004B2E24")

    _functions_ = {
 #QueryInterface -> riid:REFIID, ppvObject:**void
 "QueryInterface": ctypes.WINFUNCTYPE(HRESULT, REFIID, POINTER(PVOID))(0, "QueryInterface"),
 #AddRef -> 
 "AddRef": ctypes.WINFUNCTYPE(ULONG)(1, "AddRef"),
 #Release -> 
 "Release": ctypes.WINFUNCTYPE(ULONG)(2, "Release"),
 #GetQualifierSet -> ppQualSet:**IWbemQualifierSet
 "GetQualifierSet": ctypes.WINFUNCTYPE(HRESULT, POINTER(PVOID))(3, "GetQualifierSet"),
 #Get -> wszName:LPCWSTR, lFlags:LONG, pVal:*VARIANT, pType:*CIMTYPE, plFlavor:*LONG
 "Get": ctypes.WINFUNCTYPE(HRESULT, LPCWSTR, LONG, POINTER(VARIANT), POINTER(CIMTYPE), POINTER(LONG))(4, "Get"),
 #Put -> wszName:LPCWSTR, lFlags:LONG, pVal:*VARIANT, Type:CIMTYPE
 "Put": ctypes.WINFUNCTYPE(HRESULT, LPCWSTR, LONG, POINTER(VARIANT), CIMTYPE)(5, "Put"),
 #Delete -> wszName:LPCWSTR
 "Delete": ctypes.WINFUNCTYPE(HRESULT, LPCWSTR)(6, "Delete"),
 #GetNames -> wszQualifierName:LPCWSTR, lFlags:LONG, pQualifierVal:*VARIANT, pNames:**SAFEARRAY
 "GetNames": ctypes.WINFUNCTYPE(HRESULT, LPCWSTR, LONG, POINTER(VARIANT), POINTER(POINTER(SAFEARRAY)))(7, "GetNames"),
 #BeginEnumeration -> lEnumFlags:LONG
 "BeginEnumeration": ctypes.WINFUNCTYPE(HRESULT, LONG)(8, "BeginEnumeration"),
 #Next -> lFlags:LONG, strName:*BSTR, pVal:*VARIANT, pType:*CIMTYPE, plFlavor:*LONG
 "Next": ctypes.WINFUNCTYPE(HRESULT, LONG, POINTER(BSTR), POINTER(VARIANT), POINTER(CIMTYPE), POINTER(LONG))(9, "Next"),
 #EndEnumeration -> 
 "EndEnumeration": ctypes.WINFUNCTYPE(HRESULT)(10, "EndEnumeration"),
 #GetPropertyQualifierSet -> wszProperty:LPCWSTR, ppQualSet:**IWbemQualifierSet
 "GetPropertyQualifierSet": ctypes.WINFUNCTYPE(HRESULT, LPCWSTR, POINTER(PVOID))(11, "GetPropertyQualifierSet"),
 #Clone -> ppCopy:**IWbemClassObject
 "Clone": ctypes.WINFUNCTYPE(HRESULT, POINTER(PVOID))(12, "Clone"),
 #GetObjectText -> lFlags:LONG, pstrObjectText:*BSTR
 "GetObjectText": ctypes.WINFUNCTYPE(HRESULT, LONG, POINTER(BSTR))(13, "GetObjectText"),
 #SpawnDerivedClass -> lFlags:LONG, ppNewClass:**IWbemClassObject
 "SpawnDerivedClass": ctypes.WINFUNCTYPE(HRESULT, LONG, POINTER(PVOID))(14, "SpawnDerivedClass"),
 #SpawnInstance -> lFlags:LONG, ppNewInstance:**IWbemClassObject
 "SpawnInstance": ctypes.WINFUNCTYPE(HRESULT, LONG, POINTER(PVOID))(15, "SpawnInstance"),
 #CompareTo -> lFlags:LONG, pCompareTo:*IWbemClassObject
 "CompareTo": ctypes.WINFUNCTYPE(HRESULT, LONG, PVOID)(16, "CompareTo"),
 #GetPropertyOrigin -> wszName:LPCWSTR, pstrClassName:*BSTR
 "GetPropertyOrigin": ctypes.WINFUNCTYPE(HRESULT, LPCWSTR, POINTER(BSTR))(17, "GetPropertyOrigin"),
 #InheritsFrom -> strAncestor:LPCWSTR
 "InheritsFrom": ctypes.WINFUNCTYPE(HRESULT, LPCWSTR)(18, "InheritsFrom"),
 #GetMethod -> wszName:LPCWSTR, lFlags:LONG, ppInSignature:**IWbemClassObject, ppOutSignature:**IWbemClassObject
 "GetMethod": ctypes.WINFUNCTYPE(HRESULT, LPCWSTR, LONG, POINTER(PVOID), POINTER(PVOID))(19, "GetMethod"),
 #PutMethod -> wszName:LPCWSTR, lFlags:LONG, pInSignature:*IWbemClassObject, pOutSignature:*IWbemClassObject
 "PutMethod": ctypes.WINFUNCTYPE(HRESULT, LPCWSTR, LONG, PVOID, PVOID)(20, "PutMethod"),
 #DeleteMethod -> wszName:LPCWSTR
 "DeleteMethod": ctypes.WINFUNCTYPE(HRESULT, LPCWSTR)(21, "DeleteMethod"),
 #BeginMethodEnumeration -> lEnumFlags:LONG
 "BeginMethodEnumeration": ctypes.WINFUNCTYPE(HRESULT, LONG)(22, "BeginMethodEnumeration"),
 #NextMethod -> lFlags:LONG, pstrName:*BSTR, ppInSignature:**IWbemClassObject, ppOutSignature:**IWbemClassObject
 "NextMethod": ctypes.WINFUNCTYPE(HRESULT, LONG, POINTER(BSTR), POINTER(PVOID), POINTER(PVOID))(23, "NextMethod"),
 #EndMethodEnumeration -> 
 "EndMethodEnumeration": ctypes.WINFUNCTYPE(HRESULT)(24, "EndMethodEnumeration"),
 #GetMethodQualifierSet -> wszMethod:LPCWSTR, ppQualSet:**IWbemQualifierSet
 "GetMethodQualifierSet": ctypes.WINFUNCTYPE(HRESULT, LPCWSTR, POINTER(PVOID))(25, "GetMethodQualifierSet"),
 #GetMethodOrigin -> wszMethodName:LPCWSTR, pstrClassName:*BSTR
 "GetMethodOrigin": ctypes.WINFUNCTYPE(HRESULT, LPCWSTR, POINTER(BSTR))(26, "GetMethodOrigin"),
    }


class IWbemContext(COMInterface):
    IID = generate_IID(0x44ACA674, 0xE8FC, 0x11D0, 0xA0, 0x7C, 0x00, 0xC0, 0x4F, 0xB6, 0x88, 0x20, name="IWbemContext", strid="44ACA674-E8FC-11D0-A07C-00C04FB68820")

    _functions_ = {
 #QueryInterface -> riid:REFIID, ppvObject:**void
 "QueryInterface": ctypes.WINFUNCTYPE(HRESULT, REFIID, POINTER(PVOID))(0, "QueryInterface"),
 #AddRef -> 
 "AddRef": ctypes.WINFUNCTYPE(ULONG)(1, "AddRef"),
 #Release -> 
 "Release": ctypes.WINFUNCTYPE(ULONG)(2, "Release"),
 #Clone -> ppNewCopy:**IWbemContext
 "Clone": ctypes.WINFUNCTYPE(HRESULT, POINTER(PVOID))(3, "Clone"),
 #GetNames -> lFlags:LONG, pNames:**SAFEARRAY
 "GetNames": ctypes.WINFUNCTYPE(HRESULT, LONG, POINTER(POINTER(SAFEARRAY)))(4, "GetNames"),
 #BeginEnumeration -> lFlags:LONG
 "BeginEnumeration": ctypes.WINFUNCTYPE(HRESULT, LONG)(5, "BeginEnumeration"),
 #Next -> lFlags:LONG, pstrName:*BSTR, pValue:*VARIANT
 "Next": ctypes.WINFUNCTYPE(HRESULT, LONG, POINTER(BSTR), POINTER(VARIANT))(6, "Next"),
 #EndEnumeration -> 
 "EndEnumeration": ctypes.WINFUNCTYPE(HRESULT)(7, "EndEnumeration"),
 #SetValue -> wszName:LPCWSTR, lFlags:LONG, pValue:*VARIANT
 "SetValue": ctypes.WINFUNCTYPE(HRESULT, LPCWSTR, LONG, POINTER(VARIANT))(8, "SetValue"),
 #GetValue -> wszName:LPCWSTR, lFlags:LONG, pValue:*VARIANT
 "GetValue": ctypes.WINFUNCTYPE(HRESULT, LPCWSTR, LONG, POINTER(VARIANT))(9, "GetValue"),
 #DeleteValue -> wszName:LPCWSTR, lFlags:LONG
 "DeleteValue": ctypes.WINFUNCTYPE(HRESULT, LPCWSTR, LONG)(10, "DeleteValue"),
 #DeleteAll -> 
 "DeleteAll": ctypes.WINFUNCTYPE(HRESULT)(11, "DeleteAll"),
    }


class IWbemLocator(COMInterface):
    IID = generate_IID(0xDC12A687, 0x737F, 0x11CF, 0x88, 0x4D, 0x00, 0xAA, 0x00, 0x4B, 0x2E, 0x24, name="IWbemLocator", strid="DC12A687-737F-11CF-884D-00AA004B2E24")

    _functions_ = {
 #QueryInterface -> riid:REFIID, ppvObject:**void
 "QueryInterface": ctypes.WINFUNCTYPE(HRESULT, REFIID, POINTER(PVOID))(0, "QueryInterface"),
 #AddRef -> 
 "AddRef": ctypes.WINFUNCTYPE(ULONG)(1, "AddRef"),
 #Release -> 
 "Release": ctypes.WINFUNCTYPE(ULONG)(2, "Release"),
 #ConnectServer -> strNetworkResource:BSTR, strUser:BSTR, strPassword:BSTR, strLocale:BSTR, lSecurityFlags:LONG, strAuthority:BSTR, pCtx:*IWbemContext, ppNamespace:**IWbemServices
 "ConnectServer": ctypes.WINFUNCTYPE(HRESULT, BSTR, BSTR, BSTR, BSTR, LONG, BSTR, PVOID, POINTER(PVOID))(3, "ConnectServer"),
    }


class IWbemObjectSink(COMInterface):
    IID = generate_IID(0x7C857801, 0x7381, 0x11CF, 0x88, 0x4D, 0x00, 0xAA, 0x00, 0x4B, 0x2E, 0x24, name="IWbemObjectSink", strid="7C857801-7381-11CF-884D-00AA004B2E24")

    _functions_ = {
 #QueryInterface -> riid:REFIID, ppvObject:**void
 "QueryInterface": ctypes.WINFUNCTYPE(HRESULT, REFIID, POINTER(PVOID))(0, "QueryInterface"),
 #AddRef -> 
 "AddRef": ctypes.WINFUNCTYPE(ULONG)(1, "AddRef"),
 #Release -> 
 "Release": ctypes.WINFUNCTYPE(ULONG)(2, "Release"),
 #Indicate -> lObjectCount:LONG, apObjArray:**IWbemClassObject
 "Indicate": ctypes.WINFUNCTYPE(HRESULT, LONG, POINTER(PVOID))(3, "Indicate"),
 #SetStatus -> lFlags:LONG, hResult:HRESULT, strParam:BSTR, pObjParam:*IWbemClassObject
 "SetStatus": ctypes.WINFUNCTYPE(HRESULT, LONG, HRESULT, BSTR, PVOID)(4, "SetStatus"),
    }


class IWbemQualifierSet(COMInterface):
    IID = generate_IID(0xDC12A680, 0x737F, 0x11CF, 0x88, 0x4D, 0x00, 0xAA, 0x00, 0x4B, 0x2E, 0x24, name="IWbemQualifierSet", strid="DC12A680-737F-11CF-884D-00AA004B2E24")

    _functions_ = {
 #QueryInterface -> riid:REFIID, ppvObject:**void
 "QueryInterface": ctypes.WINFUNCTYPE(HRESULT, REFIID, POINTER(PVOID))(0, "QueryInterface"),
 #AddRef -> 
 "AddRef": ctypes.WINFUNCTYPE(ULONG)(1, "AddRef"),
 #Release -> 
 "Release": ctypes.WINFUNCTYPE(ULONG)(2, "Release"),
 #Get -> wszName:LPCWSTR, lFlags:LONG, pVal:*VARIANT, plFlavor:*LONG
 "Get": ctypes.WINFUNCTYPE(HRESULT, LPCWSTR, LONG, POINTER(VARIANT), POINTER(LONG))(3, "Get"),
 #Put -> wszName:LPCWSTR, pVal:*VARIANT, lFlavor:LONG
 "Put": ctypes.WINFUNCTYPE(HRESULT, LPCWSTR, POINTER(VARIANT), LONG)(4, "Put"),
 #Delete -> wszName:LPCWSTR
 "Delete": ctypes.WINFUNCTYPE(HRESULT, LPCWSTR)(5, "Delete"),
 #GetNames -> lFlags:LONG, pNames:**SAFEARRAY
 "GetNames": ctypes.WINFUNCTYPE(HRESULT, LONG, POINTER(POINTER(SAFEARRAY)))(6, "GetNames"),
 #BeginEnumeration -> lFlags:LONG
 "BeginEnumeration": ctypes.WINFUNCTYPE(HRESULT, LONG)(7, "BeginEnumeration"),
 #Next -> lFlags:LONG, pstrName:*BSTR, pVal:*VARIANT, plFlavor:*LONG
 "Next": ctypes.WINFUNCTYPE(HRESULT, LONG, POINTER(BSTR), POINTER(VARIANT), POINTER(LONG))(8, "Next"),
 #EndEnumeration -> 
 "EndEnumeration": ctypes.WINFUNCTYPE(HRESULT)(9, "EndEnumeration"),
    }


class IWbemServices(COMInterface):
    IID = generate_IID(0x9556DC99, 0x828C, 0x11CF, 0xA3, 0x7E, 0x00, 0xAA, 0x00, 0x32, 0x40, 0xC7, name="IWbemServices", strid="9556DC99-828C-11CF-A37E-00AA003240C7")

    _functions_ = {
 #QueryInterface -> riid:REFIID, ppvObject:**void
 "QueryInterface": ctypes.WINFUNCTYPE(HRESULT, REFIID, POINTER(PVOID))(0, "QueryInterface"),
 #AddRef -> 
 "AddRef": ctypes.WINFUNCTYPE(ULONG)(1, "AddRef"),
 #Release -> 
 "Release": ctypes.WINFUNCTYPE(ULONG)(2, "Release"),
 #OpenNamespace -> strNamespace:BSTR, lFlags:LONG, pCtx:*IWbemContext, ppWorkingNamespace:**IWbemServices, ppResult:**IWbemCallResult
 "OpenNamespace": ctypes.WINFUNCTYPE(HRESULT, BSTR, LONG, PVOID, POINTER(PVOID), POINTER(PVOID))(3, "OpenNamespace"),
 #CancelAsyncCall -> pSink:*IWbemObjectSink
 "CancelAsyncCall": ctypes.WINFUNCTYPE(HRESULT, PVOID)(4, "CancelAsyncCall"),
 #QueryObjectSink -> lFlags:LONG, ppResponseHandler:**IWbemObjectSink
 "QueryObjectSink": ctypes.WINFUNCTYPE(HRESULT, LONG, POINTER(PVOID))(5, "QueryObjectSink"),
 #GetObject -> strObjectPath:BSTR, lFlags:LONG, pCtx:*IWbemContext, ppObject:**IWbemClassObject, ppCallResult:**IWbemCallResult
 "GetObject": ctypes.WINFUNCTYPE(HRESULT, BSTR, LONG, PVOID, POINTER(PVOID), POINTER(PVOID))(6, "GetObject"),
 #GetObjectAsync -> strObjectPath:BSTR, lFlags:LONG, pCtx:*IWbemContext, pResponseHandler:*IWbemObjectSink
 "GetObjectAsync": ctypes.WINFUNCTYPE(HRESULT, BSTR, LONG, PVOID, PVOID)(7, "GetObjectAsync"),
 #PutClass -> pObject:*IWbemClassObject, lFlags:LONG, pCtx:*IWbemContext, ppCallResult:**IWbemCallResult
 "PutClass": ctypes.WINFUNCTYPE(HRESULT, PVOID, LONG, PVOID, POINTER(PVOID))(8, "PutClass"),
 #PutClassAsync -> pObject:*IWbemClassObject, lFlags:LONG, pCtx:*IWbemContext, pResponseHandler:*IWbemObjectSink
 "PutClassAsync": ctypes.WINFUNCTYPE(HRESULT, PVOID, LONG, PVOID, PVOID)(9, "PutClassAsync"),
 #DeleteClass -> strClass:BSTR, lFlags:LONG, pCtx:*IWbemContext, ppCallResult:**IWbemCallResult
 "DeleteClass": ctypes.WINFUNCTYPE(HRESULT, BSTR, LONG, PVOID, POINTER(PVOID))(10, "DeleteClass"),
 #DeleteClassAsync -> strClass:BSTR, lFlags:LONG, pCtx:*IWbemContext, pResponseHandler:*IWbemObjectSink
 "DeleteClassAsync": ctypes.WINFUNCTYPE(HRESULT, BSTR, LONG, PVOID, PVOID)(11, "DeleteClassAsync"),
 #CreateClassEnum -> strSuperclass:BSTR, lFlags:LONG, pCtx:*IWbemContext, ppEnum:**IEnumWbemClassObject
 "CreateClassEnum": ctypes.WINFUNCTYPE(HRESULT, BSTR, LONG, PVOID, POINTER(PVOID))(12, "CreateClassEnum"),
 #CreateClassEnumAsync -> strSuperclass:BSTR, lFlags:LONG, pCtx:*IWbemContext, pResponseHandler:*IWbemObjectSink
 "CreateClassEnumAsync": ctypes.WINFUNCTYPE(HRESULT, BSTR, LONG, PVOID, PVOID)(13, "CreateClassEnumAsync"),
 #PutInstance -> pInst:*IWbemClassObject, lFlags:LONG, pCtx:*IWbemContext, ppCallResult:**IWbemCallResult
 "PutInstance": ctypes.WINFUNCTYPE(HRESULT, PVOID, LONG, PVOID, POINTER(PVOID))(14, "PutInstance"),
 #PutInstanceAsync -> pInst:*IWbemClassObject, lFlags:LONG, pCtx:*IWbemContext, pResponseHandler:*IWbemObjectSink
 "PutInstanceAsync": ctypes.WINFUNCTYPE(HRESULT, PVOID, LONG, PVOID, PVOID)(15, "PutInstanceAsync"),
 #DeleteInstance -> strObjectPath:BSTR, lFlags:LONG, pCtx:*IWbemContext, ppCallResult:**IWbemCallResult
 "DeleteInstance": ctypes.WINFUNCTYPE(HRESULT, BSTR, LONG, PVOID, POINTER(PVOID))(16, "DeleteInstance"),
 #DeleteInstanceAsync -> strObjectPath:BSTR, lFlags:LONG, pCtx:*IWbemContext, pResponseHandler:*IWbemObjectSink
 "DeleteInstanceAsync": ctypes.WINFUNCTYPE(HRESULT, BSTR, LONG, PVOID, PVOID)(17, "DeleteInstanceAsync"),
 #CreateInstanceEnum -> strFilter:BSTR, lFlags:LONG, pCtx:*IWbemContext, ppEnum:**IEnumWbemClassObject
 "CreateInstanceEnum": ctypes.WINFUNCTYPE(HRESULT, BSTR, LONG, PVOID, POINTER(PVOID))(18, "CreateInstanceEnum"),
 #CreateInstanceEnumAsync -> strFilter:BSTR, lFlags:LONG, pCtx:*IWbemContext, pResponseHandler:*IWbemObjectSink
 "CreateInstanceEnumAsync": ctypes.WINFUNCTYPE(HRESULT, BSTR, LONG, PVOID, PVOID)(19, "CreateInstanceEnumAsync"),
 #ExecQuery -> strQueryLanguage:BSTR, strQuery:BSTR, lFlags:LONG, pCtx:*IWbemContext, ppEnum:**IEnumWbemClassObject
 "ExecQuery": ctypes.WINFUNCTYPE(HRESULT, BSTR, BSTR, LONG, PVOID, POINTER(PVOID))(20, "ExecQuery"),
 #ExecQueryAsync -> strQueryLanguage:BSTR, strQuery:BSTR, lFlags:LONG, pCtx:*IWbemContext, pResponseHandler:*IWbemObjectSink
 "ExecQueryAsync": ctypes.WINFUNCTYPE(HRESULT, BSTR, BSTR, LONG, PVOID, PVOID)(21, "ExecQueryAsync"),
 #ExecNotificationQuery -> strQueryLanguage:BSTR, strQuery:BSTR, lFlags:LONG, pCtx:*IWbemContext, ppEnum:**IEnumWbemClassObject
 "ExecNotificationQuery": ctypes.WINFUNCTYPE(HRESULT, BSTR, BSTR, LONG, PVOID, POINTER(PVOID))(22, "ExecNotificationQuery"),
 #ExecNotificationQueryAsync -> strQueryLanguage:BSTR, strQuery:BSTR, lFlags:LONG, pCtx:*IWbemContext, pResponseHandler:*IWbemObjectSink
 "ExecNotificationQueryAsync": ctypes.WINFUNCTYPE(HRESULT, BSTR, BSTR, LONG, PVOID, PVOID)(23, "ExecNotificationQueryAsync"),
 #ExecMethod -> strObjectPath:BSTR, strMethodName:BSTR, lFlags:LONG, pCtx:*IWbemContext, pInParams:*IWbemClassObject, ppOutParams:**IWbemClassObject, ppCallResult:**IWbemCallResult
 "ExecMethod": ctypes.WINFUNCTYPE(HRESULT, BSTR, BSTR, LONG, PVOID, PVOID, POINTER(PVOID), POINTER(PVOID))(24, "ExecMethod"),
 #ExecMethodAsync -> strObjectPath:BSTR, strMethodName:BSTR, lFlags:LONG, pCtx:*IWbemContext, pInParams:*IWbemClassObject, pResponseHandler:*IWbemObjectSink
 "ExecMethodAsync": ctypes.WINFUNCTYPE(HRESULT, BSTR, BSTR, LONG, PVOID, PVOID, PVOID)(25, "ExecMethodAsync"),
    }
