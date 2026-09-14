using System;
using System.Collections;
using System.Collections.Generic;
using System.Diagnostics;
using System.Reflection;
using System.Runtime.CompilerServices;
using System.Runtime.InteropServices;
using System.Threading.Tasks;
using System.Timers;
using System.Windows;
using System.Windows.Threading;
using GCUService.MySystem.Battry;
using Microsoft.Win32;
using MyControlCenter;

namespace GCUService.MySystem
{
	internal class BatteryProtection
	{
		[StructLayout(LayoutKind.Auto)]
		[CompilerGenerated]
		private struct <AutoCorrection>d__76 : IAsyncStateMachine
		{
			public int <>1__state;

			public AsyncVoidMethodBuilder <>t__builder;

			public BatteryProtection <>4__this;

			public object sender;

			private void MoveNext()
			{
			//Invalid MethodBodyBlock: Invalid method header: 0x2C
			}

			void IAsyncStateMachine.MoveNext()
			{
				//ILSpy generated this explicit interface implementation from .override directive in MoveNext
				this.MoveNext();
			}

			[DebuggerHidden]
			private void SetStateMachine(IAsyncStateMachine stateMachine)
			{
				//IL_0000: Unknown result type (might be due to invalid IL or missing references)
				_ = /*Error near IL_0001: Stack underflow*/- /*Error near IL_0001: Stack underflow*/;
				/*Error near IL_0001: Unknown opcode: 0xE5*/;
			}

			void IAsyncStateMachine.SetStateMachine(IAsyncStateMachine stateMachine)
			{
				//ILSpy generated this explicit interface implementation from .override directive in SetStateMachine
				this.SetStateMachine(stateMachine);
			}
		}

		[StructLayout(LayoutKind.Auto)]
		[CompilerGenerated]
		private struct <Receive>d__91 : IAsyncStateMachine
		{
			public int <>1__state;

			public AsyncVoidMethodBuilder <>t__builder;

			public byte[] message;

			public BatteryProtection <>4__this;

			private object <tmp2>5__2;

			private TaskAwaiter<object> <>u__1;

			private TaskAwaiter <>u__2;

			private void MoveNext()
			{
				/*Error: Unknown opcode: 0xC4*/;
			}

			void IAsyncStateMachine.MoveNext()
			{
				//ILSpy generated this explicit interface implementation from .override directive in MoveNext
				this.MoveNext();
			}

			[DebuggerHidden]
			private void SetStateMachine(IAsyncStateMachine stateMachine)
			{
			//Invalid MethodBodyBlock: Invalid method header: 0x78
			}

			void IAsyncStateMachine.SetStateMachine(IAsyncStateMachine stateMachine)
			{
				//ILSpy generated this explicit interface implementation from .override directive in SetStateMachine
				this.SetStateMachine(stateMachine);
			}
		}

		[StructLayout(LayoutKind.Auto)]
		[CompilerGenerated]
		private struct <NotificationShow>d__92 : IAsyncStateMachine
		{
			public int <>1__state;

			public AsyncVoidMethodBuilder <>t__builder;

			public string stageStatus;

			public BatteryProtection <>4__this;

			private TaskAwaiter <>u__1;

			private void MoveNext()
			{
			//Invalid MethodBodyBlock: Invalid method header: 0x27 0x5B
			}

			void IAsyncStateMachine.MoveNext()
			{
				//ILSpy generated this explicit interface implementation from .override directive in MoveNext
				this.MoveNext();
			}

			[DebuggerHidden]
			private void SetStateMachine(IAsyncStateMachine stateMachine)
			{
			//Invalid MethodBodyBlock: Invalid method header: 0x54
			}

			void IAsyncStateMachine.SetStateMachine(IAsyncStateMachine stateMachine)
			{
				//ILSpy generated this explicit interface implementation from .override directive in SetStateMachine
				this.SetStateMachine(stateMachine);
			}
		}

		[StructLayout(LayoutKind.Auto)]
		[CompilerGenerated]
		private struct <ReflashUIString>d__96 : IAsyncStateMachine
		{
			public int <>1__state;

			public AsyncTaskMethodBuilder<object> <>t__builder;

			public BatteryProtection <>4__this;

			private object <fileResource>5__2;

			private TaskAwaiter<object> <>u__1;

			private void MoveNext()
			{
			//Invalid MethodBodyBlock: Invalid method header: 0xBC
			}

			void IAsyncStateMachine.MoveNext()
			{
				//ILSpy generated this explicit interface implementation from .override directive in MoveNext
				this.MoveNext();
			}

			[DebuggerHidden]
			private void SetStateMachine(IAsyncStateMachine stateMachine)
			{
			//Invalid MethodBodyBlock: Invalid method header: 0x91
			}

			void IAsyncStateMachine.SetStateMachine(IAsyncStateMachine stateMachine)
			{
				//ILSpy generated this explicit interface implementation from .override directive in SetStateMachine
				this.SetStateMachine(stateMachine);
			}
		}

		[StructLayout(LayoutKind.Auto)]
		[CompilerGenerated]
		private struct <LoadLanguageResourceFromPath>d__97<T> : IAsyncStateMachine
		{
			public int <>1__state;

			public AsyncTaskMethodBuilder<T> <>t__builder;

			public string language;

			private TaskAwaiter<T> <>u__1;

			private void MoveNext()
			{
			//Invalid MethodBodyBlock: Invalid method header: 0x9F 0x5D
			}

			void IAsyncStateMachine.MoveNext()
			{
				//ILSpy generated this explicit interface implementation from .override directive in MoveNext
				this.MoveNext();
			}

			[DebuggerHidden]
			private void SetStateMachine(IAsyncStateMachine stateMachine)
			{
			//Invalid MethodBodyBlock: Invalid method header: 0x95
			}

			void IAsyncStateMachine.SetStateMachine(IAsyncStateMachine stateMachine)
			{
				//ILSpy generated this explicit interface implementation from .override directive in SetStateMachine
				this.SetStateMachine(stateMachine);
			}
		}

		private static readonly BatteryProtection BatteryProtectionmodel;

		public MqttClientCtrl m_MQTTClient;

		private BatteryPercentManger battry;

		private Timer _Timer;

		private DateTime ApInstalledTime;

		private DateTime OpenOSTime;

		private DateTime OpenHealthTime;

		private int PowerProtectionMin;

		private int PowerProtectionMax;

		private int PowerCorrectionMin;

		private int PowerCorrectionMax;

		private bool _ProtecionSwitch;

		private bool _CorretionSwitch;

		private bool _NotificationSwitch;

		private string _FinishDateTime;

		private uint _HealthProtectionStauts;

		private uint _BatteryPowerStatus;

		private bool _BatteryProctionSupport;

		private STAGE_STATUS _ProtectionSTAGE1;

		private STAGE_STATUS _ProtectionSTAGE2;

		private STAGE_STATUS _CorrenctionSTAGE1;

		private STAGE_STATUS _CorrenctionSTAGE2;

		private STAGE_STATUS _CorrenctionSTAGE3;

		private const string m_sRegistryPath = "\\OEM\\GamingCenter2\\BatteryProtection";

		public static List<NotificationWindow> _dialogs;

		private int i;

		private string m_sLang;

		private string m_sRegPath;

		private Dispatcher mainDispatcher;

		public static BatteryProtection Instance
		{
			get
			{
			//Invalid MethodBodyBlock: Invalid method header: 0xD7 0x44
			}
		}

		private string FinishDateTime
		{
			get
			{
			//Invalid MethodBodyBlock: Invalid method header: 0x8C
			}
			set
			{
			//Invalid MethodBodyBlock: Invalid method header: 0x98
			}
		}

		public bool NotificationSwitch
		{
			get
			{
			//Invalid MethodBodyBlock: Invalid method header: 0x30
			}
			set
			{
			//Invalid MethodBodyBlock: Invalid method header: 0xA4
			}
		}

		public bool CorretionSwitch
		{
			get
			{
			//Invalid MethodBodyBlock: Invalid method header: 0xA7 0x0A
			}
			set
			{
			//Invalid MethodBodyBlock: Invalid method header: 0xCC
			}
		}

		public bool ProtectionSwitch
		{
			get
			{
			//Invalid MethodBodyBlock: Invalid method header: 0xBC
			}
			set
			{
			//Invalid MethodBodyBlock: Invalid method header: 0xBC
			}
		}

		public uint HealthProtectionStauts
		{
			get
			{
			//Invalid MethodBodyBlock: Invalid method header: 0x97 0x6E
			}
			set
			{
			//Invalid MethodBodyBlock: Invalid method header: 0xFB 0x91
			}
		}

		public uint BatteryPowerStatus
		{
			get
			{
			//Invalid MethodBodyBlock: Invalid method header: 0x7C
			}
			set
			{
			//Invalid MethodBodyBlock: Invalid method header: 0x44
			}
		}

		public bool BatteryProctionSupport
		{
			get
			{
			//Invalid MethodBodyBlock: Invalid method header: 0x1F 0x1A
			}
			set
			{
				//IL_0005: Unknown result type (might be due to invalid IL or missing references)
				if (/*Error near IL_0005: Stack underflow*/ > /*Error near IL_0005: Stack underflow*/)
				{
					/*Error: Invalid branch target*/;
				}
				_ = /*Error near IL_0006: Stack underflow*/& /*Error near IL_0006: Stack underflow*/;
				/*Error near IL_0006: Not a type handle*/;
			}
		}

		public STAGE_STATUS ProtectionSTAGE1
		{
			get
			{
			//Invalid MethodBodyBlock: Invalid method header: 0xFC
			}
			set
			{
			//Invalid MethodBodyBlock: Invalid method header: 0x77 0x48
			}
		}

		public STAGE_STATUS ProtectionSTAGE2
		{
			get
			{
				//IL_0004: Expected F4, but got I4
				((float[])/*Error near IL_0004: Stack underflow*/)[/*Error near IL_0004: Stack underflow*/] = checked((int)/*Error: ldarg 176 (out-of-bounds)*/);
				/*Error near IL_0004: Invalid metadata token*/;
			}
			set
			{
				/*Error: Unknown opcode: 0xEA*/;
			}
		}

		public STAGE_STATUS CorrenctionSTAGE1
		{
			get
			{
			//Invalid MethodBodyBlock: Invalid method header: 0x6C
			}
			set
			{
			//Invalid MethodBodyBlock: Invalid method header: 0xC8
			}
		}

		public STAGE_STATUS CorrenctionSTAGE2
		{
			get
			{
				//IL_0006: Unknown result type (might be due to invalid IL or missing references)
				//IL_0008: Expected F4, but got Unknown
				((long[])/*Error near IL_0001: Stack underflow*/)[/*Error near IL_0001: Stack underflow*/] = (long)/*Error near IL_0001: Stack underflow*/;
				if (/*Error near IL_0006: Stack underflow*/ != /*Error near IL_0006: Stack underflow*/)
				{
					/*Error: Invalid branch target*/;
				}
				((float[])/*Error near IL_0008: Stack underflow*/)[/*Error near IL_0008: Stack underflow*/] = checked(/*Error near IL_0007: Stack underflow*/ * /*Error near IL_0007: Stack underflow*/);
				/*Error near IL_0008: ldloc 193 (out-of-bounds)*/;
				_ = 0;
				/*Error near IL_000b: stloc 3 (out-of-bounds)*/;
				_ = 1;
				/*Error near IL_000d: Unknown opcode: 0xAA*/;
			}
			set
			{
			//Invalid MethodBodyBlock: Invalid method header: 0xA0
			}
		}

		public STAGE_STATUS CorrenctionSTAGE3
		{
			get
			{
			//Invalid MethodBodyBlock: Invalid method header: 0x9C
			}
			set
			{
			//Invalid MethodBodyBlock: Invalid method header: 0x1F 0xBB
			}
		}

		private BatteryProtection()
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x37 0x8B
		}

		public void Resume()
		{
		//Invalid MethodBodyBlock: Invalid method header: 0xAB 0x14
		}

		private void SystemEvents_PowerModeChanged(object sender, PowerModeChangedEventArgs e)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0xA8
		}

		private void InitializePowerCorrectionStatus()
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x25
		}

		private void setHealthProtectinStatus()
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x73 0xEF
		}

		private void InitializeHealthSwitch()
		{
		//Invalid MethodBodyBlock: Invalid method header: 0xE1
		}

		public void SetHealthSwitch(bool enable)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x80
		}

		public void SetProtectionHigh()
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x28
		}

		public void SetProtectionMiddle()
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x49
		}

		public void SetProtectionLow()
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x68
		}

		private byte ConvertToByte(BitArray bits)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x89
		}

		private void Battry_LifePercentChange_Auto(object sender, EventArgs e)
		{
			/*Error: Unknown opcode: 0xE5*/;
		}

		private void Battry_LifePercentChange(object sender, EventArgs e)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0xA0
		}

		private void AutoProtection(object sender)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x58
		}

		[AsyncStateMachine(typeof(<AutoCorrection>d__76))]
		private void AutoCorrection(object sender)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x8B 0x4E
		}

		private void Reset()
		{
		//Invalid MethodBodyBlock: Invalid method header: 0xB7 0x46
		}

		private bool LoadSwitchFromRegistry(string Name)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x97 0x91
		}

		private STAGE_STATUS LoadStatusFromRegistry(string StageName)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x64
		}

		private string LoadStatusFromRegistryString(string StageName)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x0F 0xAF
		}

		private void SaveToRegistryString(string StageName, object stage)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x83 0xD7
		}

		private void SaveToRegistry(string StageName, object stage)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x8C
		}

		private void SendToUI(dynamic status)
		{
			/*Error: Metadata token must be either a methoddef, memberref or methodspec*/;
		}

		private void _Timer_Elapsed(object sender, ElapsedEventArgs e)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x80
		}

		private void CorrectionTime(int days)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0xDF 0xB6
		}

		public void AllPowerStatus()
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x9D
		}

		private double GetTopFrom()
		{
		//Invalid MethodBodyBlock: Invalid method header: 0xCF 0x47
		}

		private void Dialog_Closed(object sender, EventArgs e)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0xD7 0x1D
		}

		[AsyncStateMachine(typeof(<Receive>d__91))]
		internal void Receive(byte[] message)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x75
		}

		[AsyncStateMachine(typeof(<NotificationShow>d__92))]
		private void NotificationShow(string stageStatus)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x9D
		}

		private ResourceDictionary SetResourceDictionary()
		{
		//Invalid MethodBodyBlock: Invalid method header: 0xAD
		}

		[AsyncStateMachine(typeof(<ReflashUIString>d__96))]
		private Task<dynamic> ReflashUIString(ResourceDictionary dict)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0xB3 0x52
		}

		[AsyncStateMachine(typeof(<LoadLanguageResourceFromPath>d__97<>))]
		private static Task<T> LoadLanguageResourceFromPath<T>(string language, Assembly assembly)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0xE9
		}

		internal void SetDispatcher(Dispatcher dispatcher)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0xC3 0x8A
		}
	}
}
You are not using the latest version of the tool, please update.
Latest version is '11.0.0.9375' (yours is '9.1.0-no-branch')
