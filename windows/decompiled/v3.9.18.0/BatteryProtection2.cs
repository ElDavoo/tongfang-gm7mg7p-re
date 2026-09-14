using System;
using System.Collections;
using System.Diagnostics;
using System.Runtime.CompilerServices;
using System.Runtime.InteropServices;
using System.Timers;
using Microsoft.Win32;
using MyControlCenter;
using MyECIO;

namespace GCUService.MySystem
{
	internal class BatteryProtection2
	{
		private enum BatteryHealthProtection_Status
		{
			PERFORMANCEDMODE,
			BALANCEDMODE,
			HEALTHYMODE
		}

		private enum Battery_Commands
		{
			GET,
			CHARGING_UP_LIMIT,
			CHARGING_DOWN_LIMIT,
			RECOVERY,
			TYPE_C_ADAPTOR_PRIORITY_SWITCH_ON,
			TYPE_C_ADAPTOR_PRIORITY_SWITCH_OFF
		}

		[StructLayout(LayoutKind.Auto)]
		[CompilerGenerated]
		private struct <Receive>d__36 : IAsyncStateMachine
		{
			public int <>1__state;

			public AsyncVoidMethodBuilder <>t__builder;

			public byte[] message;

			public BatteryProtection2 <>4__this;

			private TaskAwaiter<object> <>u__1;

			private void MoveNext()
			{
				_ = 8;
				/*Error near IL_0001: Invalid field token*/;
			}

			void IAsyncStateMachine.MoveNext()
			{
				//ILSpy generated this explicit interface implementation from .override directive in MoveNext
				this.MoveNext();
			}

			[DebuggerHidden]
			private void SetStateMachine(IAsyncStateMachine stateMachine)
			{
			//Invalid MethodBodyBlock: Invalid method header: 0xE7 0xB7
			}

			void IAsyncStateMachine.SetStateMachine(IAsyncStateMachine stateMachine)
			{
				//ILSpy generated this explicit interface implementation from .override directive in SetStateMachine
				this.SetStateMachine(stateMachine);
			}
		}

		private string className;

		private static readonly BatteryProtection2 BatteryProtectionmodel;

		public MqttClientCtrl m_MQTTClient;

		private MyEcCtrl EcCtrl;

		private BatteryPercentManger battry;

		private Timer _Timer;

		private string m_sRegCurrentPath;

		private int m_HealthProtectionStatus;

		private int m_BatteryChargingLimit_Up_Default;

		private int m_BatteryChargingLimit_Down_Default;

		private int m_TypeCAdaptorPrioritySwitch;

		private bool m_TypeCAdaptorPrioritySupport;

		private int m_nCustomizeTarget;

		private uint _BatteryPowerStatus;

		private int _BatteryChargingLimit_Up;

		private int _BatteryChargingLimit_Down;

		private int _BatteryLimitationMode;

		public static BatteryProtection2 Instance
		{
			get
			{
			//Invalid MethodBodyBlock: Invalid method header: 0x3B 0x98
			}
		}

		public uint BatteryPowerStatus
		{
			get
			{
			//Invalid MethodBodyBlock: Invalid method header: 0xC7 0xA2
			}
			set
			{
				//IL_0000: Unknown result type (might be due to invalid IL or missing references)
				checked
				{
					_ = (short)(/*Error near IL_0001: Stack underflow*/ & /*Error near IL_0001: Stack underflow*/);
					/*Error near IL_0002: Invalid metadata token*/;
				}
			}
		}

		private int m_BatteryChargingLimit_Up
		{
			get
			{
				/*Error: stloc 229 (out-of-bounds)*/;
				/*Error near IL_0002: Not a type handle*/;
			}
			set
			{
			//Invalid MethodBodyBlock: Invalid method header: 0x2C
			}
		}

		private unsafe int m_BatteryChargingLimit_Down
		{
			get
			{
				/*Error: ldloc 3 (out-of-bounds)*/;
				/*Error near IL_0001: Unknown opcode: 0xAC*/;
			}
			set
			{
				//IL_0000: Unknown result type (might be due to invalid IL or missing references)
				_ = *(short*)(IntPtr)(/*Error near IL_0001: Stack underflow*/ / /*Error near IL_0001: Stack underflow*/);
				/*Error near IL_0002: Unknown opcode: 0xAF*/;
			}
		}

		private int m_BatteryLimitationMode
		{
			get
			{
			//Invalid MethodBodyBlock: Invalid method header: 0x84
			}
			set
			{
			//Invalid MethodBodyBlock: Invalid method header: 0x8B 0x4B
			}
		}

		private BatteryProtection2()
		{
		//Invalid MethodBodyBlock: Invalid method header: 0xA0
		}

		public void EnableByService()
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x39
		}

		public void Resume()
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x63 0x9F
		}

		[AsyncStateMachine(typeof(<Receive>d__36))]
		public void Receive(byte[] message)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x78
		}

		private void Init()
		{
			if (/*Error near IL_0002: Stack underflow*/ < /*Error near IL_0002: Stack underflow*/)
			{
				/*Error: Invalid branch target*/;
			}
			/*Error near IL_0002: Unknown opcode: 0xA6*/;
		}

		private void LoadBatteryLimitationDefault()
		{
		//Invalid MethodBodyBlock: Invalid method header: 0xD0
		}

		public void Uninstall()
		{
		//Invalid MethodBodyBlock: Invalid method header: 0xB8
		}

		public void Disable()
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x53 0xA1
		}

		private void SetRegistry(string name, int value)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0xA7 0xD7
		}

		private void SetHealthProtectionStatus()
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x6B 0xB1
		}

		private void SetHealthProtectionHigh()
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x4D
		}

		private void SetHealthProtectionMiddle()
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x30
		}

		private unsafe void SetHealthProtectionLow()
		{
			if (/*Error near IL_0002: Stack underflow*/ < /*Error near IL_0002: Stack underflow*/)
			{
				/*Error: Invalid branch target*/;
			}
			*(?*)(IntPtr)/*Error near IL_0003: Stack underflow*/ = /*Error near IL_0003: Stack underflow*/;
			((object[])/*Error near IL_0004: Stack underflow*/)[/*Error near IL_0004: Stack underflow*/] = (object)/*Error near IL_0004: Stack underflow*/;
			/*Error near IL_0004: Unknown opcode: 0xBF*/;
		}

		private byte ConvertToByte(BitArray bits)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x89
		}

		private void SetTypeCAdaptorSwitch(int status)
		{
			//IL_0001: Unknown result type (might be due to invalid IL or missing references)
			_ = /*Error near IL_0002: Stack underflow*// checked((int)/*Error near IL_0001: Stack underflow*/);
			/*Error near IL_0002: Unknown opcode: 0xF3*/;
		}

		private void SetBatteryChargingLimit_Up(int limit)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x45
		}

		private int ReadBatteryChargingLimit_Up()
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x78
		}

		private void SetBatteryChargingLimit_Down(int limit)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0xF8
		}

		private int ReadBatteryChargingLimit_Down()
		{
			/*Error: Unknown opcode: 0xF3*/;
		}

		private void SystemEvents_PowerModeChanged(object sender, PowerModeChangedEventArgs e)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x24
		}

		private void Battry_LifePercentChange(object sender, EventArgs e)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x07 0xF0
		}

		private void SendToUI(dynamic status)
		{
			/*Error: Empty body found. Decompiled assembly might be a reference assembly.*/;
		}

		private void UpdateStatusToClient()
		{
			//IL_0002: Unknown result type (might be due to invalid IL or missing references)
			((long[])/*Error near IL_0001: Stack underflow*/)[/*Error near IL_0001: Stack underflow*/] = (long)/*Error near IL_0001: Stack underflow*/;
			_ = (float)checked(/*Error near IL_0003: Stack underflow*/ + (double)/*Error near IL_0002: Stack underflow*/);
			/*Error near IL_0004: Unknown opcode: 0xAD*/;
		}
	}
}
You are not using the latest version of the tool, please update.
Latest version is '11.0.0.9375' (yours is '9.1.0-no-branch')
