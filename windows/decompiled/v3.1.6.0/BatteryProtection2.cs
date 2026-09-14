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
		private struct <Receive>d__35 : IAsyncStateMachine
		{
			public int <>1__state;

			public AsyncVoidMethodBuilder <>t__builder;

			public byte[] message;

			public BatteryProtection2 <>4__this;

			private TaskAwaiter<object> <>u__1;

			private void MoveNext()
			{
			//Invalid MethodBodyBlock: Invalid method header: 0x9F 0x7F
			}

			void IAsyncStateMachine.MoveNext()
			{
				//ILSpy generated this explicit interface implementation from .override directive in MoveNext
				this.MoveNext();
			}

			[DebuggerHidden]
			private void SetStateMachine(IAsyncStateMachine stateMachine)
			{
				//IL_0001: Invalid comparison between Unknown and I
				if ((long)(IntPtr)/*Error near IL_0003: Stack underflow*/ <= (long)((IntPtr[])/*Error near IL_0001: Stack underflow*/)[/*Error near IL_0001: Stack underflow*/])
				{
					if (checked((IntPtr)(long)unchecked((ulong)checked((long)(byte)/*Error near IL_0004: Stack underflow*/))) == (IntPtr)0)
					{
						/*Error: Invalid branch target*/;
					}
					/*Error near IL_000c: Metadata token must be either a methoddef, memberref or methodspec*/;
				}
				if (/*Error near IL_0021: Stack underflow*/ >= /*Error near IL_0021: Stack underflow*/)
				{
					/*Error: Invalid branch target*/;
				}
				/*Error near IL_0021: Stack underflow*/;
				/*Error near IL_0022: Unknown opcode: 0xFB*/;
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

		private uint _BatteryPowerStatus;

		private int _BatteryChargingLimit_Up;

		private int _BatteryChargingLimit_Down;

		private int _BatteryLimitationMode;

		public static BatteryProtection2 Instance
		{
			get
			{
				/*Error: Unknown opcode: 0xED*/;
			}
		}

		public uint BatteryPowerStatus
		{
			get
			{
			//Invalid MethodBodyBlock: Invalid method header: 0xF7 0xCE
			}
			set
			{
			//Invalid MethodBodyBlock: Invalid method header: 0xD1
			}
		}

		private int m_BatteryChargingLimit_Up
		{
			get
			{
			//Invalid MethodBodyBlock: Invalid method header: 0x1D
			}
			set
			{
				//IL_000b: Unknown result type (might be due to invalid IL or missing references)
				_ = /*Error near IL_000c: Stack underflow*/>> 0;
				/*Error: End of method reached without returning.*/;
			}
		}

		private int m_BatteryChargingLimit_Down
		{
			get
			{
			//Invalid MethodBodyBlock: Invalid method header: 0x71
			}
			set
			{
			//Invalid MethodBodyBlock: Invalid method header: 0x6D
			}
		}

		private int m_BatteryLimitationMode
		{
			get
			{
			//Invalid MethodBodyBlock: Invalid method header: 0x01
			}
			set
			{
			//Invalid MethodBodyBlock: Invalid method header: 0x71
			}
		}

		private BatteryProtection2()
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x68
		}

		public void EnableByService()
		{
		//Invalid MethodBodyBlock: Invalid method header: 0xB3 0x98
		}

		public void Resume()
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x93 0xC8
		}

		[AsyncStateMachine(typeof(<Receive>d__35))]
		public void Receive(byte[] message)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x49
		}

		private void Init()
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x79
		}

		private void LoadBatteryLimitationDefault()
		{
			//IL_0000: Unknown result type (might be due to invalid IL or missing references)
			_ = /*Error near IL_0001: Stack underflow*// /*Error near IL_0001: Stack underflow*/;
			/*Error near IL_0002: Unknown opcode: 0xF5*/;
		}

		public void Uninstall()
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x15
		}

		public void Disable()
		{
			//IL_0000: Unknown result type (might be due to invalid IL or missing references)
			//IL_0002: Expected I4, but got Unknown
			//IL_0004: Unknown result type (might be due to invalid IL or missing references)
			//IL_0006: Expected O, but got Unknown
			//IL_0007: Unknown result type (might be due to invalid IL or missing references)
			((short[])/*Error near IL_0002: Stack underflow*/)[/*Error near IL_0002: Stack underflow*/] = (short)(/*Error near IL_0001: Stack underflow*/ / /*Error near IL_0001: Stack underflow*/);
			if (/*Error near IL_0004: Stack underflow*/ != /*Error near IL_0004: Stack underflow*/)
			{
				/*Error: Invalid branch target*/;
			}
			checked
			{
				_ = /*Error near IL_0008: Stack underflow*/* ((Array)unchecked(/*Error near IL_0005: Stack underflow*/ - /*Error near IL_0005: Stack underflow*/)).Length;
				/*Error near IL_0008: ldarg 1 (out-of-bounds)*/;
				/*Error: End of method reached without returning.*/;
			}
		}

		private void SetRegistry(string name, int value)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x04
		}

		private void SetHealthProtectionStatus()
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x51
		}

		private void SetHealthProtectionHigh()
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x9B 0xE9
		}

		private void SetHealthProtectionMiddle()
		{
		//Invalid MethodBodyBlock: Invalid method header: 0xBD
		}

		private void SetHealthProtectionLow()
		{
			/*Error: Unknown opcode: 0x78*/;
		}

		private byte ConvertToByte(BitArray bits)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0xC4
		}

		private void SetTypeCAdaptorSwitch(int status)
		{
			/*Error: Not a type handle*/;
		}

		private void SetBatteryChargingLimit_Up(int limit)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x9B 0x88
		}

		private int ReadBatteryChargingLimit_Up()
		{
		//Invalid MethodBodyBlock: Invalid method header: 0xF5
		}

		private void SetBatteryChargingLimit_Down(int limit)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x43 0x20
		}

		private int ReadBatteryChargingLimit_Down()
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x2D
		}

		private void SystemEvents_PowerModeChanged(object sender, PowerModeChangedEventArgs e)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x55
		}

		private void Battry_LifePercentChange(object sender, EventArgs e)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0xE0
		}

		private void SendToUI(dynamic status)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x95
		}

		private void UpdateStatusToClient()
		{
		//Invalid MethodBodyBlock: Invalid method header: 0xB5
		}
	}
}
