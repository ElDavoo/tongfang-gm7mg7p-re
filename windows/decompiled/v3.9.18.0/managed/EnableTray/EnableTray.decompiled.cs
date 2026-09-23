using System;
using System.CodeDom.Compiler;
using System.Collections.Generic;
using System.ComponentModel;
using System.Configuration;
using System.Diagnostics;
using System.Globalization;
using System.Reflection;
using System.Resources;
using System.Runtime.CompilerServices;
using System.Runtime.InteropServices;
using System.Runtime.Versioning;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Markup;
using EnableTray.DataService;
using Microsoft.Win32;
using uPLibrary.Networking.M2Mqtt;
using uPLibrary.Networking.M2Mqtt.Messages;

[assembly: CompilationRelaxations(8)]
[assembly: RuntimeCompatibility(WrapNonExceptionThrows = true)]
[assembly: Debuggable(DebuggableAttribute.DebuggingModes.IgnoreSymbolStoreSequencePoints)]
[assembly: AssemblyTitle("EnableTray")]
[assembly: AssemblyDescription("")]
[assembly: AssemblyConfiguration("")]
[assembly: AssemblyCompany("")]
[assembly: AssemblyProduct("EnableTray")]
[assembly: AssemblyCopyright("Copyright ©  2020")]
[assembly: AssemblyTrademark("")]
[assembly: ComVisible(false)]
[assembly: ThemeInfo(/*Could not decode attribute arguments.*/)]
[assembly: AssemblyFileVersion("1.0.0.0")]
[assembly: TargetFramework(".NETFramework,Version=v4.6.2", FrameworkDisplayName = ".NET Framework 4.6.2")]
[assembly: AssemblyVersion("1.0.0.0")]
[module: ConfusedBy("Confuser.Core 1.2.0+4110faee9d")]
[module: SuppressIldasm]
internal class <Module>
{
	static <Module>()
	{
		\u200b\u206b\u206b\u202a\u206d\u200f\u206d\u200c\u206a\u206a\u206f\u202e\u200f\u202d\u202c\u200e\u206d\u200d\u200c\u202b\u200e\u202b\u206b\u202b\u206a\u202a\u206f\u200f\u206c\u206e\u202a\u200b\u206b\u200e\u202d\u200d\u200c\u202e\u206f\u206b\u202e();
		\u200f\u202b\u206c\u206e\u200c\u200d\u200b\u202d\u206e\u206c\u206c\u206f\u200e\u202a\u202b\u200d\u200d\u202a\u200c\u202e\u202e\u206b\u202d\u202a\u200b\u206d\u200f\u206c\u202d\u200f\u200d\u200f\u202b\u206d\u206f\u200f\u206a\u206a\u206c\u206a\u202e();
		\u206d\u200f\u206f\u202b\u202d\u206f\u206e\u202b\u202b\u200d\u200e\u206a\u202b\u200d\u200f\u206a\u206f\u206b\u206c\u206e\u206d\u202e\u200d\u206d\u206b\u200b\u206d\u202a\u202c\u206b\u200b\u206e\u206c\u202b\u200f\u200e\u202a\u206e\u206a\u200e\u202e();
	}

	private static void \u206d\u200f\u206f\u202b\u202d\u206f\u206e\u202b\u202b\u200d\u200e\u206a\u202b\u200d\u200f\u206a\u206f\u206b\u206c\u206e\u206d\u202e\u200d\u206d\u206b\u200b\u206d\u202a\u202c\u206b\u200b\u206e\u206c\u202b\u200f\u200e\u202a\u206e\u206a\u200e\u202e()
	{
	//Invalid MethodBodyBlock: Invalid method header: 0x13 0xFC
	}

	private static void \u202e\u206f\u200c\u202d\u200f\u206d\u200c\u202d\u206a\u200b\u206c\u200d\u200b\u206a\u206c\u206c\u206f\u202b\u206b\u202c\u200c\u200c\u200e\u200b\u200d\u202c\u206e\u202d\u202d\u206f\u200c\u202b\u202c\u206e\u206e\u202a\u206e\u202a\u200d\u202e(object P_0)
	{
	//Invalid MethodBodyBlock: Invalid method header: 0xF7 0x02
	}

	[DllImport("kernel32.dll", EntryPoint = "VirtualProtect")]
	internal unsafe static extern bool \u206f\u206d\u202a\u200b\u200d\u206f\u200e\u200f\u202d\u200d\u206b\u200b\u202b\u202c\u200c\u200e\u200b\u202d\u206c\u202c\u200b\u200e\u202a\u202e\u200e\u206a\u206d\u202a\u206e\u202c\u200e\u200b\u200c\u206d\u206c\u206d\u206a\u206f\u202b\u206b\u202e(byte* P_0, int P_1, uint P_2, ref uint P_3);

	internal static void \u200f\u202b\u206c\u206e\u200c\u200d\u200b\u202d\u206e\u206c\u206c\u206f\u200e\u202a\u202b\u200d\u200d\u202a\u200c\u202e\u202e\u206b\u202d\u202a\u200b\u206d\u200f\u206c\u202d\u200f\u200d\u200f\u202b\u206d\u206f\u200f\u206a\u206a\u206c\u206a\u202e()
	{
		/*Error: Metadata token must be either a methoddef, memberref or methodspec*/;
	}

	[DllImport("kernel32.dll", EntryPoint = "VirtualProtect")]
	internal static extern bool \u200f\u202c\u202e\u200d\u200f\u200f\u200b\u200e\u206e\u202d\u206e\u200b\u206b\u200c\u200e\u202d\u206c\u202e\u206c\u200c\u202b\u200c\u200c\u206b\u202b\u200e\u200b\u206b\u200c\u206a\u206d\u202a\u200c\u206d\u202d\u200b\u202b\u206e\u202a\u200d\u202e(IntPtr P_0, uint P_1, uint P_2, ref uint P_3);

	internal unsafe static void \u200b\u206b\u206b\u202a\u206d\u200f\u206d\u200c\u206a\u206a\u206f\u202e\u200f\u202d\u202c\u200e\u206d\u200d\u200c\u202b\u200e\u202b\u206b\u202b\u206a\u202a\u206f\u200f\u206c\u206e\u202a\u200b\u206b\u200e\u202d\u200d\u200c\u202e\u206f\u206b\u202e()
	{
		Module module = typeof(global::<Module>).Module;
		string fullyQualifiedName = module.FullyQualifiedName;
		bool flag = fullyQualifiedName.Length > 0 && fullyQualifiedName[0] == '<';
		byte* ptr = (byte*)(void*)Marshal.GetHINSTANCE(module);
		byte* intPtr = ptr + (uint)((int*)ptr)[15];
		ushort num = ((ushort*)intPtr)[3];
		ushort num2 = ((ushort*)intPtr)[10];
		uint* ptr2 = null;
		uint num3 = 0u;
		uint* ptr3 = (uint*)(intPtr + 24 + (int)num2);
		uint num4 = 476944802u;
		uint num5 = 477493873u;
		uint num6 = 328169042u;
		uint num7 = 218283818u;
		for (int i = 0; i < num; i++)
		{
			switch (*(ptr3++) * *(ptr3++))
			{
			case 708183100u:
				ptr2 = (uint*)(ptr + (flag ? ptr3[3] : ptr3[1]));
				num3 = (flag ? ptr3[2] : (*ptr3)) >> 2;
				break;
			default:
			{
				uint* ptr4 = (uint*)(ptr + (flag ? ptr3[3] : ptr3[1]));
				uint num8 = ptr3[2] >> 2;
				for (uint num9 = 0u; num9 < num8; num9++)
				{
					uint num10 = (num4 ^ *(ptr4++)) + num5 + num6 * num7;
					num4 = num5;
					num5 = num6;
					num5 = num7;
					num7 = num10;
				}
				break;
			}
			case 0u:
				break;
			}
			ptr3 += 8;
		}
		uint[] array = new uint[16];
		uint[] array2 = new uint[16];
		for (int j = 0; j < 16; j++)
		{
			array[j] = num7;
			array2[j] = num5;
			num4 = (num5 >> 5) | (num5 << 27);
			num5 = (num6 >> 3) | (num6 << 29);
			num6 = (num7 >> 7) | (num7 << 25);
			num7 = (num4 >> 11) | (num4 << 21);
		}
		array[0] = array[0] ^ array2[0];
		array[1] = array[1] * array2[1];
		array[2] = array[2] + array2[2];
		array[3] = array[3] ^ array2[3];
		array[4] = array[4] * array2[4];
		array[5] = array[5] + array2[5];
		array[6] = array[6] ^ array2[6];
		array[7] = array[7] * array2[7];
		array[8] = array[8] + array2[8];
		array[9] = array[9] ^ array2[9];
		array[10] = array[10] * array2[10];
		array[11] = array[11] + array2[11];
		array[12] = array[12] ^ array2[12];
		array[13] = array[13] * array2[13];
		array[14] = array[14] + array2[14];
		array[15] = array[15] ^ array2[15];
		uint num11 = 64u;
		\u200f\u202c\u202e\u200d\u200f\u200f\u200b\u200e\u206e\u202d\u206e\u200b\u206b\u200c\u200e\u202d\u206c\u202e\u206c\u200c\u202b\u200c\u200c\u206b\u202b\u200e\u200b\u206b\u200c\u206a\u206d\u202a\u200c\u206d\u202d\u200b\u202b\u206e\u202a\u200d\u202e((IntPtr)ptr2, num3 << 2, num11, ref num11);
		if (num11 != 64)
		{
			uint num12 = 0u;
			for (uint num13 = 0u; num13 < num3; num13++)
			{
				*ptr2 ^= array[num12 & 0xF];
				array[num12 & 0xF] = (array[num12 & 0xF] ^ *(ptr2++)) + 1035675673;
				num12++;
			}
		}
	}
}
namespace EnableTray
{
	public class App : Application
	{
		private readonly MqttWrap mqttwarp;

		private void Application_Startup(object sender, StartupEventArgs e)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x11
		}

		private unsafe void Application_Exit(object sender, ExitEventArgs e)
		{
			_ = *(byte*)(IntPtr)/*Error near IL_0001: Stack underflow*/;
			/*Error near IL_0001: Unknown opcode: 0xA6*/;
		}

		[DebuggerNonUserCode]
		[GeneratedCode("PresentationBuildTasks", "4.0.0.0")]
		public void InitializeComponent()
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x5D
		}

		[STAThread]
		[DebuggerNonUserCode]
		[GeneratedCode("PresentationBuildTasks", "4.0.0.0")]
		public static void Main()
		{
		//Invalid MethodBodyBlock: Invalid method header: 0xA8
		}
	}
	public class MainWindow : Window, IComponentConnector
	{
		private bool _contentLoaded;

		[DebuggerNonUserCode]
		[GeneratedCode("PresentationBuildTasks", "4.0.0.0")]
		public void InitializeComponent()
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x9D
		}

		[DebuggerNonUserCode]
		[GeneratedCode("PresentationBuildTasks", "4.0.0.0")]
		[EditorBrowsable(EditorBrowsableState.Never)]
		void IComponentConnector.Connect(int connectionId, object target)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x95
		}
	}
	internal class Topic
	{
		public const string BatteryProtection_Control = "BatteryProtection/Control";

		public const string System_Control = "System/Control";

		public const string System_FanErrorInfo = "System/FanErrorInfo";

		public const string System_FanInfo = "System/FanInfo";

		public const string System_BatteryInfo = "System/BatteryInfo";

		public const string System_CpuInfo = "System/CpuInfo";

		public const string System_StaticsData = "System/StaticsData";

		public const string System_MemoryInfo = "System/MemoryInfo";

		public const string System_GpuInfo = "System/GpuInfo";

		public const string System_IGpuInfo = "System/IGpuInfo";

		public const string System_NetworkInfo = "System/NetworkInfo";

		public const string System_DiskInfo = "System/DiskInfo";

		public const string System_HardwareInfo = "System/HardwareInfo";

		public const string System_HwFuelGauge = "System/HwFuelGauge";

		public const string Fan_Control = "Fan/Control";

		public const string Fan_Status = "Fan/Status";

		public const string RGBLB_Control = "MyRgbLightbar/Control";

		public const string RGBLB_Status = "MyRgbLightbar/Status";

		public const string Setting_Control = "Setting/Control";

		public const string Setting_Status = "Setting/Status";

		public const string EC_Control = "EC/Control";

		public const string EC_Status = "EC/Status";

		public const string RGBKeyboard_Control = "Keyboard/Ctrl";

		public const string HIDRGBLightbar_Control = "HidLightbar/Ctrl";

		public const string Service_Close = "Service/Close";

		public const string Service_Control = "Service/Ctrl";

		public const string Customize_Control = "Customize/Control";

		public const string Customize_Info = "Customize/Info";

		public const string Languages_Info = "Languages/Info";

		public const string Languages_Control = "Languages/Control";

		public const string Openvino_Control = "Openvino/Control";

		public const string OSDTpDectect_Language = "OSDTpDectect/Language";

		public const string OSDTpDectect_Control = "OSDTpDectect/Control";

		public const string OSD_Status = "OSD/Status";
	}
	internal class MqttWrap
	{
		[StructLayout(LayoutKind.Auto)]
		[CompilerGenerated]
		private struct <SendTopicToServer>d__10 : IAsyncStateMachine
		{
			public int <>1__state;

			public AsyncVoidMethodBuilder <>t__builder;

			public string topic;

			public object data;

			public bool save;

			public MqttWrap <>4__this;

			private void MoveNext()
			{
			//Invalid MethodBodyBlock: Invalid method header: 0xF9
			}

			void IAsyncStateMachine.MoveNext()
			{
				//ILSpy generated this explicit interface implementation from .override directive in MoveNext
				this.MoveNext();
			}

			[DebuggerHidden]
			private void SetStateMachine(IAsyncStateMachine stateMachine)
			{
			//Invalid MethodBodyBlock: Invalid method header: 0x69
			}

			void IAsyncStateMachine.SetStateMachine(IAsyncStateMachine stateMachine)
			{
				//ILSpy generated this explicit interface implementation from .override directive in SetStateMachine
				this.SetStateMachine(stateMachine);
			}
		}

		private MqttDataService MqttDataService;

		private static readonly MqttWrap MqttWrapInstance;

		public bool ConnectionStatus;

		private bool shutdown_called;

		public static MqttWrap CreateInstance
		{
			get
			{
				if (/*Error near IL_0005: Stack underflow*/ >= /*Error near IL_0005: Stack underflow*/)
				{
					/*Error: Invalid branch target*/;
				}
				/*Error near IL_0005: Unknown opcode: 0xA6*/;
			}
		}

		private unsafe MqttWrap()
		{
			checked
			{
				_ = unchecked((long)(IntPtr)(void*)(ulong)checked((UIntPtr)/*Error near IL_0001: Stack underflow*/)) * 7725777216909136958L;
				/*Error near IL_000b: Read out of bounds.*/;
			}
		}

		private void OnConnect(bool connectionSatus)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x77 0xCD
		}

		private void OnConnectFail()
		{
		//Invalid MethodBodyBlock: Invalid method header: 0xC8
		}

		private void OnPublishReceived(ushort MessageId)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x9B 0x09
		}

		public void MqttDisconncet()
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x09
		}

		[AsyncStateMachine(typeof(<SendTopicToServer>d__10))]
		public void SendTopicToServer(string topic, object data, bool save = true)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0xA4
		}

		private void Shutdown()
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x81
		}
	}
}
namespace EnableTray.Properties
{
	[GeneratedCode("System.Resources.Tools.StronglyTypedResourceBuilder", "4.0.0.0")]
	[DebuggerNonUserCode]
	[CompilerGenerated]
	internal class Resources
	{
		private static ResourceManager resourceMan;

		private static CultureInfo resourceCulture;

		[EditorBrowsable(EditorBrowsableState.Advanced)]
		internal static ResourceManager ResourceManager
		{
			get
			{
			//Invalid MethodBodyBlock: Invalid method header: 0x4B 0xD8
			}
		}

		[EditorBrowsable(EditorBrowsableState.Advanced)]
		internal static CultureInfo Culture
		{
			get
			{
			//Invalid MethodBodyBlock: Invalid method header: 0xE0
			}
			set
			{
			//Invalid MethodBodyBlock: Invalid method header: 0x95
			}
		}

		internal Resources()
		{
		//Invalid MethodBodyBlock: Invalid method header: 0xA3 0xE8
		}
	}
	[CompilerGenerated]
	[GeneratedCode("Microsoft.VisualStudio.Editors.SettingsDesigner.SettingsSingleFileGenerator", "11.0.0.0")]
	internal sealed class Settings : ApplicationSettingsBase
	{
		private static Settings defaultInstance;

		public static Settings Default
		{
			get
			{
			//Invalid MethodBodyBlock: Invalid method header: 0x73 0x10
			}
		}

		public Settings()
		{
			if (/*Error near IL_0005: Stack underflow*/ < /*Error near IL_0005: Stack underflow*/)
			{
				/*Error: Invalid branch target*/;
			}
			((sbyte[])/*Error near IL_0008: Stack underflow*/)[/*Error near IL_0008: Stack underflow*/] = (sbyte)(byte)/*Error near IL_0005: ldarg 1 (out-of-bounds)*/;
			/*Error near IL_0008: Unknown opcode: 0xFA*/;
		}
	}
}
namespace EnableTray.DataService
{
	internal class MqttDataService
	{
		public delegate void MqttDataServiceDataHandler(object topic, object data);

		public delegate void ClientConnectionHandler(bool connection);

		public delegate void ClientConnectionFailHandler();

		public delegate void PublishedHandler(ushort MessageId);

		[StructLayout(LayoutKind.Auto)]
		[CompilerGenerated]
		private struct <ClientConnection>d__28 : IAsyncStateMachine
		{
			public int <>1__state;

			public AsyncVoidMethodBuilder <>t__builder;

			public MqttDataService <>4__this;

			private void MoveNext()
			{
			//Invalid MethodBodyBlock: Invalid method header: 0x28
			}

			void IAsyncStateMachine.MoveNext()
			{
				//ILSpy generated this explicit interface implementation from .override directive in MoveNext
				this.MoveNext();
			}

			[DebuggerHidden]
			private void SetStateMachine(IAsyncStateMachine stateMachine)
			{
			//Invalid MethodBodyBlock: Invalid method header: 0xE4
			}

			void IAsyncStateMachine.SetStateMachine(IAsyncStateMachine stateMachine)
			{
				//ILSpy generated this explicit interface implementation from .override directive in SetStateMachine
				this.SetStateMachine(stateMachine);
			}
		}

		[StructLayout(LayoutKind.Auto)]
		[CompilerGenerated]
		private struct <Client_MqttMsgPublishReceived>d__34 : IAsyncStateMachine
		{
			public int <>1__state;

			public AsyncVoidMethodBuilder <>t__builder;

			public MqttMsgPublishEventArgs e;

			public MqttDataService <>4__this;

			private string <message>5__2;

			private TaskAwaiter<object> <>u__1;

			private void MoveNext()
			{
			//Invalid MethodBodyBlock: Invalid method header: 0x09
			}

			void IAsyncStateMachine.MoveNext()
			{
				//ILSpy generated this explicit interface implementation from .override directive in MoveNext
				this.MoveNext();
			}

			[DebuggerHidden]
			private void SetStateMachine(IAsyncStateMachine stateMachine)
			{
			//Invalid MethodBodyBlock: Invalid method header: 0x00
			}

			void IAsyncStateMachine.SetStateMachine(IAsyncStateMachine stateMachine)
			{
				//ILSpy generated this explicit interface implementation from .override directive in SetStateMachine
				this.SetStateMachine(stateMachine);
			}
		}

		[CompilerGenerated]
		private sealed class <>c__DisplayClass35_0
		{
			public MqttDataService <>4__this;

			public int ret;

			public string topic;

			public string msg;

			public bool save;

			internal void <PublishTopic>b__0()
			{
			//Invalid MethodBodyBlock: Invalid method header: 0xCF 0xAA
			}
		}

		[StructLayout(LayoutKind.Auto)]
		[CompilerGenerated]
		private struct <PublishTopic>d__35 : IAsyncStateMachine
		{
			public int <>1__state;

			public AsyncVoidMethodBuilder <>t__builder;

			public MqttDataService <>4__this;

			public string topic;

			public bool save;

			public object data;

			private <>c__DisplayClass35_0 <>8__1;

			private TaskAwaiter<string> <>u__1;

			private void MoveNext()
			{
			//Invalid MethodBodyBlock: Invalid method header: 0x2B 0x82
			}

			void IAsyncStateMachine.MoveNext()
			{
				//ILSpy generated this explicit interface implementation from .override directive in MoveNext
				this.MoveNext();
			}

			[DebuggerHidden]
			private void SetStateMachine(IAsyncStateMachine stateMachine)
			{
			//Invalid MethodBodyBlock: Invalid method header: 0x6D
			}

			void IAsyncStateMachine.SetStateMachine(IAsyncStateMachine stateMachine)
			{
				//ILSpy generated this explicit interface implementation from .override directive in SetStateMachine
				this.SetStateMachine(stateMachine);
			}
		}

		private static readonly MqttDataService service;

		private Dictionary<string, byte> TopicList;

		private MqttClient client;

		private string clientId;

		private string username;

		private string password;

		public static MqttDataService Instance
		{
			get
			{
			//Invalid MethodBodyBlock: Invalid method header: 0x2C
			}
		}

		public event MqttDataServiceDataHandler DataChange
		{
			[CompilerGenerated]
			add
			{
			//Invalid MethodBodyBlock: Invalid method header: 0x87 0xA3
			}
			[CompilerGenerated]
			remove
			{
				/*Error: stloc 0 (out-of-bounds)*/;
				if (/*Error near IL_0006: Stack underflow*/ == /*Error near IL_0006: Stack underflow*/)
				{
					/*Error: Invalid branch target*/;
				}
				/*Error near IL_0006: Not a type handle*/;
			}
		}

		public event ClientConnectionHandler ClientConnectionEvent
		{
			[CompilerGenerated]
			add
			{
			//Invalid MethodBodyBlock: Invalid method header: 0x0C
			}
			[CompilerGenerated]
			remove
			{
			//Invalid MethodBodyBlock: Invalid method header: 0x40
			}
		}

		public event ClientConnectionFailHandler ClientConnectionFailEvent
		{
			[CompilerGenerated]
			add
			{
			//Invalid MethodBodyBlock: Invalid method header: 0x8F 0x26
			}
			[CompilerGenerated]
			remove
			{
			//Invalid MethodBodyBlock: Invalid method header: 0x74
			}
		}

		public event PublishedHandler PublishedEventEvent
		{
			[CompilerGenerated]
			add
			{
			//Invalid MethodBodyBlock: Invalid method header: 0x8D
			}
			[CompilerGenerated]
			remove
			{
				//IL_0000: Unknown result type (might be due to invalid IL or missing references)
				//IL_0001: Unknown result type (might be due to invalid IL or missing references)
				_ = /*Error near IL_0002: Stack underflow*/- (/*Error near IL_0001: Stack underflow*/ & /*Error near IL_0001: Stack underflow*/);
				/*Error near IL_0002: Unknown opcode: 0xBC*/;
			}
		}

		private MqttDataService()
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x05
		}

		public string GetClientId()
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x68
		}

		private void InitlizeTopics()
		{
		//Invalid MethodBodyBlock: Invalid method header: 0xF5
		}

		public List<string> GetMQTT_Topics(string viewName)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x21
		}

		[AsyncStateMachine(typeof(<ClientConnection>d__28))]
		private void ClientConnection()
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x85
		}

		public void Disconnect()
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x0B 0x14
		}

		private void Client_MqttMsgPublished(object sender, MqttMsgPublishedEventArgs e)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x2C
		}

		private void Client_MqttMsgSubscribed(object sender, MqttMsgSubscribedEventArgs e)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x71
		}

		private void Client_MqttMsgUnsubscribed(object sender, MqttMsgUnsubscribedEventArgs e)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0xA7 0xE3
		}

		private void Client_ConnectionClosed(object sender, EventArgs e)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0xAD
		}

		[AsyncStateMachine(typeof(<Client_MqttMsgPublishReceived>d__34))]
		private void Client_MqttMsgPublishReceived(object sender, MqttMsgPublishEventArgs e)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x3B 0x0D
		}

		[AsyncStateMachine(typeof(<PublishTopic>d__35))]
		internal void PublishTopic(string topic, object data, bool save = true)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x1D
		}

		static MqttDataService()
		{
			switch ((sbyte)6)
			{
			default:
				/*Error: End of method reached without returning.*/;
			case 0:
				/*Error: Invalid branch target*/;
			case 1:
				/*Error: Invalid branch target*/;
			case 2:
				/*Error: Invalid branch target*/;
			case 3:
				/*Error: Invalid branch target*/;
			case 4:
				/*Error: Invalid branch target*/;
			case 5:
				/*Error: Invalid branch target*/;
			case 6:
				/*Error: Invalid branch target*/;
			case 7:
				/*Error: Invalid branch target*/;
			case 8:
				/*Error: Invalid branch target*/;
			case 9:
				/*Error: Invalid branch target*/;
			case 10:
				/*Error: Invalid branch target*/;
			case 11:
				/*Error: Invalid branch target*/;
			}
		}
	}
}
namespace Utility
{
	internal class Json
	{
		[StructLayout(LayoutKind.Auto)]
		[CompilerGenerated]
		private struct <ToObjectAsync>d__2<T> : IAsyncStateMachine
		{
			public int <>1__state;

			public AsyncTaskMethodBuilder<T> <>t__builder;

			public string value;

			private TaskAwaiter<T> <>u__1;

			private void MoveNext()
			{
			//Invalid MethodBodyBlock: Invalid method header: 0x61
			}

			void IAsyncStateMachine.MoveNext()
			{
				//ILSpy generated this explicit interface implementation from .override directive in MoveNext
				this.MoveNext();
			}

			[DebuggerHidden]
			private void SetStateMachine(IAsyncStateMachine stateMachine)
			{
			//Invalid MethodBodyBlock: Invalid method header: 0xC3 0xB9
			}

			void IAsyncStateMachine.SetStateMachine(IAsyncStateMachine stateMachine)
			{
				//ILSpy generated this explicit interface implementation from .override directive in SetStateMachine
				this.SetStateMachine(stateMachine);
			}
		}

		[StructLayout(LayoutKind.Auto)]
		[CompilerGenerated]
		private struct <StringifyAsync>d__3 : IAsyncStateMachine
		{
			public int <>1__state;

			public AsyncTaskMethodBuilder<string> <>t__builder;

			public object value;

			private TaskAwaiter<string> <>u__1;

			private void MoveNext()
			{
				//IL_0003: Expected F8, but got I8
				((double[])/*Error near IL_0003: Stack underflow*/)[/*Error near IL_0003: Stack underflow*/] = checked((long)((int[])/*Error near IL_0001: Stack underflow*/)[/*Error near IL_0001: Stack underflow*/]);
				_ = ((byte[])/*Error near IL_0004: Stack underflow*/)[/*Error near IL_0004: Stack underflow*/];
				/*Error near IL_0004: Unknown opcode: 0xF6*/;
			}

			void IAsyncStateMachine.MoveNext()
			{
				//ILSpy generated this explicit interface implementation from .override directive in MoveNext
				this.MoveNext();
			}

			[DebuggerHidden]
			private void SetStateMachine(IAsyncStateMachine stateMachine)
			{
				/*Error: Unknown opcode: 0xC4*/;
			}

			void IAsyncStateMachine.SetStateMachine(IAsyncStateMachine stateMachine)
			{
				//ILSpy generated this explicit interface implementation from .override directive in SetStateMachine
				this.SetStateMachine(stateMachine);
			}
		}

		public static T ToObject<T>(string value)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x88
		}

		public static string Stringify(object value)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0xA1
		}

		[AsyncStateMachine(typeof(<ToObjectAsync>d__2<>))]
		public static Task<T> ToObjectAsync<T>(string value)
		{
			/*Error: Unknown opcode: 0xBD*/;
		}

		[AsyncStateMachine(typeof(<StringifyAsync>d__3))]
		public static Task<string> StringifyAsync(object value)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x05
		}
	}
	internal class LogCtrl
	{
		public enum LogFileCreateMode
		{
			FollowRegistry,
			Keep,
			CreateNew
		}

		private static bool b_LogEnable;

		private static string m_LogPath;

		private static string indent_token;

		private static int indent_count;

		public static bool WithAssemblyName;

		private static readonly string AssemblyName;

		public static void SetLogPath(string logpath)
		{
			//IL_0000: Unknown result type (might be due to invalid IL or missing references)
			if (/*Error near IL_0001: Stack underflow*/ / /*Error near IL_0001: Stack underflow*/!= 0)
			{
				/*Error: Invalid branch target*/;
			}
			/*Error near IL_0008: Invalid metadata token*/;
		}

		public static void EnableLog(LogFileCreateMode create_mode = LogFileCreateMode.FollowRegistry)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0xC9
		}

		public static void DisableLog()
		{
		//Invalid MethodBodyBlock: Invalid method header: 0xC1
		}

		public static void Write(string logMessage)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x6D
		}

		public static string GetTime()
		{
		//Invalid MethodBodyBlock: Invalid method header: 0xEF 0x50
		}

		public static string GetParentDirectoryPath(string folderPath, int levels)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x13 0x08
		}

		public static string GetParentDirectoryPath(string folderPath)
		{
			//IL_0004: Expected O, but got I4
			if (/*Error near IL_0002: Stack underflow*/ != /*Error near IL_0002: Stack underflow*/)
			{
				/*Error: Invalid branch target*/;
			}
			/*Error near IL_0003: Not a type handle*/;
		}

		public static void Indent()
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x87 0x44
		}

		public static void Unindent()
		{
			/*Error: Unknown opcode: 0xF9*/;
		}

		public static void TraceMessage(string message = "", [CallerMemberName] string memberName = "", [CallerFilePath] string sourceFilePath = "", [CallerLineNumber] int sourceLineNumber = 0)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x7F 0xA1
		}

		static LogCtrl()
		{
			/*Error: Unknown opcode: 0xE6*/;
		}
	}
	internal class RegistryCtrl
	{
		public static bool m_bWriteToReg;

		public static void RegistryCurrentUserSoftwareKeyWrite(string hKey, string SubKey, string Name, object setvalue, RegistryValueKind valuekind, bool bWriteToReg)
		{
			/*Error: Unknown opcode: 0xAD*/;
		}

		public static void RegistryCurrentUserSoftwareSubKeyTreeDelete(string hKey, string SubKey)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0xB5
		}

		public static object RegistrySoftwareKeyRead(RegistryHive hKey, string SubKey, string Name, object defaultvalue)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0xF4
		}

		public static object RegistrySoftwareKeyRead(RegistryHive hKey, string SubKey, string Name, object defaultvalue, RegistryValueKind valuekind = RegistryValueKind.String)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x1D
		}

		public static void RegistrySoftwareKeyWrite(RegistryHive hKey, string SubKey, string Name, object setvalue, RegistryValueKind valuekind)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x4F 0xED
		}

		public static void RegistrySoftwareKeyDelete(RegistryHive hKey, string SubKey, string Name)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0xDF 0xBE
		}

		public static void RegistrySoftwareSubKeyDelete(RegistryHive hKey, string SubKey, string Name)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x70
		}

		public static void RegistrySoftwareSubKeyTreeDelete(RegistryHive hKey, string SubKey, string Name)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x31
		}

		public static object RegistryKeyRead(RegistryHive hKey, string SubKey, string Name, object defaultvalue)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x80
		}

		public static void RegistryKeyWrite(RegistryHive hKey, string SubKey, string Name, object setvalue, RegistryValueKind valuekind)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x51
		}

		public static int GetCustomizeTarget()
		{
		//Invalid MethodBodyBlock: Invalid method header: 0xF0
		}

		public static int GetSupportH2Ram()
		{
			//IL_0001: Invalid comparison between Unknown and I4
			if ((int)/*Error near IL_0002: Stack underflow*/ >= 6)
			{
				/*Error: Invalid branch target*/;
			}
			/*Error: End of method reached without returning.*/;
		}
	}
}
namespace Define
{
	internal static class ECSpec
	{
		[Flags]
		public enum ByteFlag
		{
			Bit0 = 1,
			Bit1 = 2,
			Bit2 = 4,
			Bit3 = 8,
			Bit4 = 0x10,
			Bit5 = 0x20,
			Bit6 = 0x40,
			Bit7 = 0x80
		}

		[Flags]
		public enum MyFanCTLByteFlag
		{
			Normal_Mode = 0,
			Turbo_Mode = 0x10,
			FanBoost_Mode = 0x40,
			User_Fan_Mode = 0x80,
			User_Fan_Level1 = 0x81,
			User_Fan_Level2 = 0x82,
			User_Fan_Level3 = 0x83,
			User_Fan_Level4 = 0x84,
			User_Fan_Level5 = 0x85,
			User_Fan_HiMode = 0xA0
		}

		[Flags]
		public enum TriggerByteFlag
		{
			WinLock_Trigger = 1,
			LightBar_Trigger = 2,
			FanBoost_Trigger = 4,
			SilentMode_Trigger = 8,
			USBCharger_Trigger = 0x10,
			RGBKeybaord_Trigger = 0x20,
			RGBLogo_Trigger = 0x40,
			RGBKeybaordWelcome_Trigger = 0x80
		}

		[Flags]
		public enum SupportByteOneFlag
		{
			AirplaneMode = 1,
			GPSSwitch = 2,
			OverClock = 4,
			MacroKey = 8,
			ShortCutKey = 0x10,
			WinLockKey = 0x20,
			LightBar = 0x40,
			FanBoost = 0x80
		}

		[Flags]
		public enum SupportByteTwoFlag
		{
			SilentMode = 1,
			USBChargerMode = 2,
			RGBKeyBoard = 4,
			MyBat = 0x40
		}

		[Flags]
		public enum SupportByteThreeFlag
		{
			FullZone = 1,
			FourZone = 2,
			FourZoneReady = 4
		}

		[Flags]
		public enum StatusByteOneFlag
		{
			WinLock = 1,
			BreathLed = 2,
			FanBoost = 4,
			MacroKey = 8,
			MyBatPowerBat = 0x10
		}

		[Flags]
		public enum RGBLightBarCtrlByteFlag
		{
			ApExit = 1,
			PowerSaveMode = 2,
			Switch_S0 = 4,
			Switch_S3 = 8,
			LB10NoKey = 0x10,
			LB10KeyPress = 0x20,
			Switch_Breath_MordenStandby = 0x40,
			WelcomeLightMode = 0x80
		}

		[Flags]
		public enum MyFan2SpeedByteFlag
		{
			Speed00 = 0,
			Speed30 = 0x3C,
			Speed35 = 0x46,
			Speed40 = 0x50,
			Speed45 = 0x5A,
			Speed50 = 0x64,
			Speed55 = 0x6E,
			Speed60 = 0x78,
			Speed70 = 0x8C
		}

		[Flags]
		public enum RGBLightbarControlByteFlag
		{
			AP_Exist = 0,
			PowerSaveMode = 2,
			S0_Switch = 4,
			S3_Switch = 8,
			Welcome = 0x80
		}

		public const ushort BIOSFuncReg = 1142;

		public const ushort ecPowSource = 1168;

		public const ushort ADDR_BIOS_INFO_3_BYTE = 1183;

		public const ushort ecBt1Temperature = 1186;

		public const ushort ecBt1RSOC = 1195;

		public const uint FAN_MODE_NORMAL = 0u;

		public const uint FAN_MODE_BOOST = 1u;

		public const uint FAN_MODE_CUSTOMIZE = 2u;

		public const uint FAN_CUSTOMIZEMODE_NORMAL = 0u;

		public const uint FAN_CUSTOMIZEMODE_BASIC = 1u;

		public const uint FAN_CUSTOMIZEMODE_HIGH = 2u;

		public const uint FAN_GAMING_MODE = 0u;

		public const uint FAN_OFFICE_MODE = 1u;

		public const uint FAN_TURBO_MODE = 2u;

		public const uint FAN_OFFICE_MODE_BASIC = 1u;

		public const uint FAN_OFFICE_MODE_ADVANCED = 2u;

		public const uint FAN_GAMING_MODE_SMART = 1u;

		public const uint FAN_GAMING_MODE_PERFENHANCED = 2u;

		public const uint POWER_SETTING_MODE_ECO = 1u;

		public const uint POWER_SETTING_MODE_STD = 2u;

		public const uint FAN_LEVEL_ZERO = 0u;

		public const uint FAN_LEVEL_ONE = 1u;

		public const uint FAN_LEVEL_TWO = 2u;

		public const uint FAN_LEVEL_THREE = 3u;

		public const uint FAN_LEVEL_FOUR = 4u;

		public const uint FAN_LEVEL_FIVE = 5u;

		public const uint TURBO_MODE_1 = 1u;

		public const uint TURBO_MODE_2 = 2u;

		public const uint TURBO_MODE_3 = 3u;

		public const uint TURBO_MODE_4 = 4u;

		public const uint TURBO_MODE_MIN = 1u;

		public const uint TURBO_MODE_MAX = 4u;

		public const uint TURBO_MODE_DEFAULT = 2u;

		public const uint QKEY_MODESWITCH = 0u;

		public const uint QKEY_FANBOOST = 1u;

		public const ushort ADDR_EC_BIF_DC_BYTE1 = 1026;

		public const ushort ADDR_EC_BIF_DC_BYTE2 = 1027;

		public const ushort ADDR_EC_BIF_DV_BYTE1 = 1032;

		public const ushort ADDR_EC_BIF_DV_BYTE2 = 1033;

		public const ushort ADDR_EC_BST_BPR_BYTE1 = 1076;

		public const ushort ADDR_EC_BST_BPR_BYTE2 = 1077;

		public const ushort ADDR_EC_BST_BRC_BYTE1 = 1078;

		public const ushort ADDR_EC_BST_BRC_BYTE2 = 1079;

		public const ushort ADDR_EC_BST_BPV_BYTE1 = 1080;

		public const ushort ADDR_EC_BST_BPV_BYTE2 = 1081;

		public const ushort ADDR_EC_BT1CycleCount_BYTE1 = 1190;

		public const ushort ADDR_EC_BT1CycleCount_BYTE2 = 1191;

		public const ushort ADDR_EC_MAIN_FAN_RPM_BYTE1 = 1124;

		public const ushort ADDR_EC_MAIN_FAN_RPM_BYTE2 = 1125;

		public const ushort ADDR_EC_BIOS_INFO5 = 1126;

		public const ushort ADDR_EC_SECOND_FAN_RPM_BYTE1 = 1132;

		public const ushort ADDR_EC_SECOND_FAN_RPM_BYTE2 = 1131;

		public const ushort ADDR_MAFAN_CONTROL_BYTE = 1873;

		public const ushort ADDR_TRIGGER_BYTE2 = 1885;

		public const ushort ADDR_SUPPORT_BYTE1 = 1893;

		public const ushort ADDR_SUPPORT_BYTE2 = 1894;

		public const ushort ADDR_PROJECT_ID_BYTE = 1856;

		public const ushort ADDR_AP_OEM_BYTE = 1857;

		public const ushort ADDR_SUPPORT_BYTE5 = 1858;

		public const ushort ADDR_MYFAN2_L1_PWM = 1859;

		public const ushort ADDR_MYFAN2_L2_PWM = 1860;

		public const ushort ADDR_MYFAN2_L3_PWM = 1861;

		public const ushort ADDR_MYFAN2_L4_PWM = 1862;

		public const ushort ADDR_MYFAN2_L5_PWM = 1863;

		public const ushort ADDR_L1_PWM_DEFAULT_MYFAN2 = 1929;

		public const ushort ADDR_L2_PWM_DEFAULT_MYFAN2 = 1930;

		public const ushort ADDR_L3_PWM_DEFAULT_MYFAN2 = 1931;

		public const ushort ADDR_L4_PWM_DEFAULT_MYFAN2 = 1932;

		public const ushort ADDR_L5_PWM_DEFAULT_MYFAN2 = 1933;

		public const ushort ADDR_BIOS_OEM_BYTE = 1870;

		public const ushort ADDR_BIOS_OEM_BYTE2 = 1922;

		public const ushort ADDR_GAMING_PL1_DEFAULT_VALUE = 1840;

		public const ushort ADDR_GAMING_PL2_DEFAULT_VALUE = 1841;

		public const ushort ADDR_GAMING_PL4_DEFAULT_VALUE = 1842;

		public const ushort ADDR_OFFICE_PL1_DEFAULT_VALUE = 1844;

		public const ushort ADDR_OFFICE_PL2_DEFAULT_VALUE = 1845;

		public const ushort ADDR_OFFICE_PL4_DEFAULT_VALUE = 1846;

		public const ushort ADDR_PL1_SETTING_VALUE = 1923;

		public const ushort ADDR_PL2_SETTING_VALUE = 1924;

		public const ushort ADDR_PL4_SETTING_VALUE = 1925;

		public const ushort ADDR_L1_PWM_DEFAULT_MYFAN3 = 1926;

		public const ushort ADDR_L2_PWM_DEFAULT_MYFAN3 = 1927;

		public const ushort ADDR_L3_PWM_DEFAULT_MYFAN3 = 1928;

		public const ushort ADDR_L4_PWM_DEFAULT_MYFAN3 = 1929;

		public const ushort ADDR_L5_PWM_DEFAULT_MYFAN3 = 1930;

		public const ushort ADDR_MYFAN3_CPU_TAU = 1848;

		public const ushort ADDR_TRIGGER_BYTE = 1895;

		public const ushort ADDR_STAUTS_BYTE = 1896;

		public const ushort ADDR_LIGHTBAR_CONTROL_BYTE = 1864;

		public const ushort ADDR_REDBAR_CONTROL_BYTE = 1865;

		public const ushort ADDR_GREENBAR_CONTROL_BYTE = 1866;

		public const ushort ADDR_BLUEBAR_CONTROL_BYTE = 1867;

		public const ushort ADDR_BATTERY_ALERT_BYTE = 1172;

		public const ushort ADDR_FAN_ALERT_BYTE = 1857;

		public const ushort ADDR_SILENTMODE_STATUS_BYTE = 1115;

		public const ushort ADDR_MYFAN3_GPU_SETTING = 1931;

		public const ushort ADDR_AP_OEM_BYTE2 = 1932;

		public const ushort ADDR_AP_OEM_BYTE6 = 1934;

		public const ushort ADDR_MYFANI_MIN_SPEED = 1950;

		public const ushort ADDR_MYFANI_MIN_TEMP = 1951;

		public const ushort ADDR_MYFANI_EXTRA_SPEED = 1952;

		public const ushort ADDR_AP_OEM_BYTE3 = 1957;

		public const ushort ADDR_AP_OEM_BYTE4 = 1958;

		public const ushort ADDR_BATTERYSAVER_PL1_DEFAULT_VALUE = 1959;

		public const ushort ADDR_BATTERYSAVER_PL2_DEFAULT_VALUE = 1960;

		public const ushort ADDR_BATTERYSAVER_PL4_DEFAULT_VALUE = 1961;

		public const ushort ADDR_BATTERYSAVER_D_DEFAULT_VALUE = 1962;

		public const ushort ADDR_MyFanCCI_Mode_Index = 1963;

		public const ushort ADDR_MyFanCCI_Mode_Profile1 = 1968;

		public const ushort ADDR_MyFanCCI_Mode_Profile2 = 1969;

		public const ushort ADDR_MyFanCCI_Mode_Profile3 = 1970;

		public const ushort ADDR_CHANGE_PORT_ID_WKD = 2043;

		public const ushort ADDR_CPU_FAN_TABLE_TEMP_UP0 = 3840;

		public const ushort ADDR_CPU_FAN_TABLE_TEMP_UP1 = 3841;

		public const ushort ADDR_CPU_FAN_TABLE_TEMP_UP2 = 3842;

		public const ushort ADDR_CPU_FAN_TABLE_TEMP_UP3 = 3843;

		public const ushort ADDR_CPU_FAN_TABLE_TEMP_UP4 = 3844;

		public const ushort ADDR_CPU_FAN_TABLE_TEMP_UP5 = 3845;

		public const ushort ADDR_CPU_FAN_TABLE_TEMP_UP6 = 3846;

		public const ushort ADDR_CPU_FAN_TABLE_TEMP_UP7 = 3847;

		public const ushort ADDR_CPU_FAN_TABLE_TEMP_UP8 = 3848;

		public const ushort ADDR_CPU_FAN_TABLE_TEMP_UP9 = 3849;

		public const ushort ADDR_CPU_FAN_TABLE_TEMP_UP10 = 3850;

		public const ushort ADDR_CPU_FAN_TABLE_TEMP_UP11 = 3851;

		public const ushort ADDR_CPU_FAN_TABLE_TEMP_UP12 = 3852;

		public const ushort ADDR_CPU_FAN_TABLE_TEMP_UP13 = 3853;

		public const ushort ADDR_CPU_FAN_TABLE_TEMP_UP14 = 3854;

		public const ushort ADDR_CPU_FAN_TABLE_TEMP_UP15 = 3855;

		public const ushort ADDR_CPU_FAN_TABLE_TEMP_DOWN0 = 3856;

		public const ushort ADDR_CPU_FAN_TABLE_TEMP_DOWN1 = 3857;

		public const ushort ADDR_CPU_FAN_TABLE_TEMP_DOWN2 = 3858;

		public const ushort ADDR_CPU_FAN_TABLE_TEMP_DOWN3 = 3859;

		public const ushort ADDR_CPU_FAN_TABLE_TEMP_DOWN4 = 3860;

		public const ushort ADDR_CPU_FAN_TABLE_TEMP_DOWN5 = 3861;

		public const ushort ADDR_CPU_FAN_TABLE_TEMP_DOWN6 = 3862;

		public const ushort ADDR_CPU_FAN_TABLE_TEMP_DOWN7 = 3863;

		public const ushort ADDR_CPU_FAN_TABLE_TEMP_DOWN8 = 3864;

		public const ushort ADDR_CPU_FAN_TABLE_TEMP_DOWN9 = 3865;

		public const ushort ADDR_CPU_FAN_TABLE_TEMP_DOWN10 = 3866;

		public const ushort ADDR_CPU_FAN_TABLE_TEMP_DOWN11 = 3867;

		public const ushort ADDR_CPU_FAN_TABLE_TEMP_DOWN12 = 3868;

		public const ushort ADDR_CPU_FAN_TABLE_TEMP_DOWN13 = 3869;

		public const ushort ADDR_CPU_FAN_TABLE_TEMP_DOWN14 = 3870;

		public const ushort ADDR_CPU_FAN_TABLE_TEMP_DOWN15 = 3871;

		public const ushort ADDR_CPU_FAN_TABLE_DUTY0 = 3872;

		public const ushort ADDR_CPU_FAN_TABLE_DUTY1 = 3873;

		public const ushort ADDR_CPU_FAN_TABLE_DUTY2 = 3874;

		public const ushort ADDR_CPU_FAN_TABLE_DUTY3 = 3875;

		public const ushort ADDR_CPU_FAN_TABLE_DUTY4 = 3876;

		public const ushort ADDR_CPU_FAN_TABLE_DUTY5 = 3877;

		public const ushort ADDR_CPU_FAN_TABLE_DUTY6 = 3878;

		public const ushort ADDR_CPU_FAN_TABLE_DUTY7 = 3879;

		public const ushort ADDR_CPU_FAN_TABLE_DUTY8 = 3880;

		public const ushort ADDR_CPU_FAN_TABLE_DUTY9 = 3881;

		public const ushort ADDR_CPU_FAN_TABLE_DUTY10 = 3882;

		public const ushort ADDR_CPU_FAN_TABLE_DUTY11 = 3883;

		public const ushort ADDR_CPU_FAN_TABLE_DUTY12 = 3884;

		public const ushort ADDR_CPU_FAN_TABLE_DUTY13 = 3885;

		public const ushort ADDR_CPU_FAN_TABLE_DUTY14 = 3886;

		public const ushort ADDR_CPU_FAN_TABLE_DUTY15 = 3887;

		public const ushort ADDR_GPU_FAN_TABLE_TEMP_UP0 = 3888;

		public const ushort ADDR_GPU_FAN_TABLE_TEMP_DOWN0 = 3904;

		public const ushort ADDR_GPU_FAN_TABLE_DUTY0 = 3920;

		public const ushort OSD_CAPSLOCK = 1;

		public const ushort OSD_NUMLOCK = 2;

		public const ushort OSD_SROLLOCK = 3;

		public const ushort OSD_TPON = 4;

		public const ushort OSD_TPOFF = 5;

		public const ushort OSD_SILENTON = 6;

		public const ushort OSD_SILENTOFF = 7;

		public const ushort OSD_WLANON = 8;

		public const ushort OSD_WLANOFF = 9;

		public const ushort OSD_WINMAXON = 10;

		public const ushort OSD_WINMAXOFF = 11;

		public const ushort OSD_BTON = 12;

		public const ushort OSD_BTOFF = 13;

		public const ushort OSD_RFON = 14;

		public const ushort OSD_RFOFF = 15;

		public const ushort OSD_3GON = 16;

		public const ushort OSD_3GOFF = 17;

		public const ushort OSD_WEBCAMON = 18;

		public const ushort OSD_WEBCAMOFF = 19;

		public const ushort OSD_BRIGHTNESSUP = 20;

		public const ushort OSD_BRIGHTNESSDOWN = 21;

		public const ushort OSD_RADIOON = 26;

		public const ushort OSD_RADIOOFF = 27;

		public const ushort OSD_POWERSAVEON = 49;

		public const ushort OSD_POWERSAVEOFF = 50;

		public const ushort OSD_MENU = 52;

		public const ushort OSD_MUTE = 53;

		public const ushort OSD_VOLUMEDOWN = 54;

		public const ushort OSD_VOLUMEUP = 55;

		public const ushort OSD_OSD_MENU_2 = 56;

		public const ushort OSD_BREATH_LED_ON = 57;

		public const ushort OSD_BREATH_LED_OFF = 58;

		public const ushort OSD_KB_LED_LEVEL0 = 59;

		public const ushort OSD_KB_LED_LEVEL1 = 60;

		public const ushort OSD_KB_LED_LEVEL2 = 61;

		public const ushort OSD_KB_LED_LEVEL3 = 62;

		public const ushort OSD_KB_LED_LEVEL4 = 63;

		public const ushort OSD_WINKEY_LOCK = 64;

		public const ushort OSD_WINKEY_UNLOCK = 65;

		public const ushort OSD_MENU_JP = 66;

		public const ushort OSD_CAMERAON = 144;

		public const ushort OSD_CAMERAOFF = 145;

		public const ushort OSD_AIRPLANEMODE = 164;

		public const ushort OSD_FANBOOST_UPDATE = 167;

		public const ushort OSD_LCD_SW = 169;

		public const ushort OSD_FAN_OVER_TEMP = 170;

		public const ushort OSD_MyBat_ACUpdate = 171;

		public const ushort OSD_MyBat_HPOff = 172;

		public const ushort OSD_Fan_DOWN_TEMP = 173;

		public const ushort OSD_Battery_Alert = 174;

		public const ushort TimAP_HaierLB_Sw = 175;

		public const ushort WinKey_Update = 165;

		public const ushort OSD_FanModeSwitch = 176;

		public const ushort BacklightLevelChange = 179;

		public const ushort BacklightPowerChange = 180;

		public const ushort TimAP_MicMute_Sw = 183;

		public const ushort OSD_FnChange = 184;

		public const int OS_VK_CAPITAL = 20;

		public const int OS_VK_NUMLOCK = 144;

		public const int OS_VK_SCROLL = 145;

		public const ushort Light_ChinaMode = 1894;

		public const ushort Light_SetToChinaMode = 1922;

		public const uint APP_Normal_Mode = 0u;

		public const uint APP_ImageProjectionLight_Mode = 1u;

		public const uint APP_LightBar_Mode = 2u;

		public const uint LEVEL_ZERO = 0u;

		public const uint LEVEL_ONE = 1u;

		public const uint LEVEL_TWO = 2u;

		public const uint LEVEL_THREE = 3u;

		public const uint LEVEL_FOUR = 4u;

		public const uint LEVEL_FIVE = 5u;

		public const uint LEVEL_SIX = 6u;

		public const uint LEVEL_SEVEN = 7u;

		public const uint LEVEL_EIGHT = 8u;

		public const uint LEVEL_NINE = 9u;

		public const uint LEVEL_MAX = 100u;

		public const int Animation_OFF = 0;

		public const int Animation_ON = 1;

		public const byte Enable_RGB_Music = 254;

		public const byte Disable_RGB_Music = 0;

		public const ushort ADDR_RGBKB_LEVEL_R = 1897;

		public const ushort ADDR_RGBKB_LEVEL_G = 1898;

		public const ushort ADDR_RGBKB_LEVEL_B = 1899;

		public const ushort ADDR_RGBKB_LEVEL_DEFAULT_R = 1900;

		public const ushort ADDR_RGBKB_LEVEL_DEFAULT_G = 1901;

		public const ushort ADDR_RGBKB_LEVEL_DEFAULT_B = 1902;

		public const ushort ADDR_RGBKB_MUSIC_NO = 1903;
	}
	internal static class APMessage
	{
		public const string WINDOW_NAME_GANINGCENTER = "GamingCenter";

		public const int WM_MSG_MYAPP = 21575;

		public const int WM_MSG_MYCOLOR2 = 21576;

		public const int WM_MSG_OSD = 1225;

		public const int WM_MSG_GAMINGCENTER = 21577;

		public const int WM_MSG_GAMINGCENTERTRAY = 21584;

		public const int WM_SYSCOMMAND = 274;

		public const int WM_QUERYENDSESSION = 17;

		public const int MSG_MYAPP_AP_OPEN = 1;

		public const int MSG_MYAPP_AP_CLOSE = 2;

		public const int MSG_MYAPP_AP_SHOW = 3;

		public const int MSG_MYAPP_AP_HIDE = 4;

		public const int MSG_MYAPP_AP_MINIMIZE = 5;

		public const int MSG_MYAPP_EVENT_WMI = 32;

		public const int SC_MONITOR_POWER_ON = 61808;
	}
	public class MyDefine
	{
		public const int status_disable = -1;

		public const int status_on = 1;

		public const int status_off = 0;

		public const int enable = 1;

		public const int disable = 0;

		public const int rgbkb_normal = 0;

		public const int rgbkb_single_zone = 1;

		public const int rgbkb_four_zone = 2;

		public const int rgbkb_full_zone = 3;

		public const int rgbkb_multiple_zone = 4;
	}
	public class SetupInfo
	{
		public const string Target_STD = "STD";

		public const string Target_Customize = "STD";
	}
	public enum ProjectID
	{
		None,
		GI,
		GJ,
		GK,
		GICN,
		GJCN,
		GK5CN_X,
		GK7CN_S,
		GK7CPCS_GK5CQ7Z,
		PF,
		GK5CP_4X_5X_6X,
		IDP,
		IDY_6Y,
		IDY_7Y,
		PF4MU_PF4MN_PF5MU,
		CML_Gaming
	}
	public enum AppLanguage
	{
		min = 0,
		en_US = 0,
		zh_CN = 1,
		tr_TR = 2,
		zh_TW = 3,
		de_DE = 4,
		hu_HU = 5,
		ko_KR = 6,
		max = 6
	}
	public class AppLanguageName
	{
		public const string en_US = "en-us";

		public const string zh_CN = "zh-cn";

		public const string tr_TR = "tr-tr";

		public const string zh_TW = "zh-tw";

		public const string de_DE = "de-de";

		public const string hu_HU = "hu-hu";

		public const string ko_KR = "ko-kr";

		public const string ru_RU = "ru-ru";

		public const string ja_JP = "ja-jp";

		public const string pl_PL = "pl-pl";

		public const string es_ES = "es-es";

		public const string fr_FR = "fr-fr";

		public const string pt_BR = "pt-br";
	}
	public enum ACLineStatus
	{
		OffLine,
		OnLine
	}
	public class PowerPlan
	{
		public const int Gaming = 1;

		public const int High = 2;

		public const int Balance = 3;

		public const int Saving = 4;
	}
	public class Customize
	{
		public const int Standard = 1;

		public const int Custom = 2;

		public const int Machenike = 3;

		public const int Mechrevo_COML = 4;

		public const int Illegear = 5;

		public const int LightMaster = 6;

		public const int Origin_PC = 7;

		public const int Monster = 8;

		public const int XMG = 9;

		public const int HASEE = 10;

		public const int MCJ = 11;

		public const int DNS = 12;

		public const int Shinelon = 13;

		public const int ONYXPC = 14;

		public const int redfox = 15;

		public const int Intel = 16;

		public const int Mechrevo = 17;

		public const int Maingear = 18;

		public const int MCJ_COML = 19;

		public const int ESI = 20;

		public const int Daten = 21;

		public const int Hansung = 22;

		public const int Eluktronics = 23;

		public const int Avell = 24;

		public const int Intel_BC = 25;

		public const int MCJ_COML2 = 1024;

		public const int ILLEGEAR_COML = 1025;

		public const int XMG_COML = 1026;
	}
	public class AppTypeNum
	{
		public const int Gaming = 1;

		public const int COML = 2;
	}
	public class FastSwitch
	{
		public const int DisplayFeatureStatusOn = 1;

		public const int DisplayFeatureStatusOff = 0;

		public const int SilentModeOn = 1;

		public const int SilentModeOff = 0;

		public const int USBChargerOff = 0;

		public const int USBChargerOn = 1;

		public const int DisplayOff = 2;

		public const int dGPUOn = 1;

		public const int dGPUOff = 0;
	}
	public class DisplayModes
	{
		public const int Stadard = 1;

		public const int Gaming = 2;

		public const int Video = 3;

		public const int Read = 4;

		public const int Customized = 5;
	}
	public class GamingCenterShow
	{
		public const int Visible = 1;

		public const int Hidden = 0;
	}
	public class PnpID
	{
		public const string CMN157D = "DISPLAY\\CMN15D7\\4&300D7CCD&2&UID265988";
	}
	public class ColorCalibrationResultCode
	{
		public const string Ready = "0";

		public const string Finish = "1";

		public const string NetworkFail = "2";

		public const string SnIsUnsupported = "3";

		public const string ColorCalibrationFail = "4";

		public const string WebClientRequestFail = "5";

		public const string ConnectServerFail = "6";

		public const string WebClientUnknownFail = "7";
	}
	public class IntelDefine
	{
		[StructLayout(LayoutKind.Sequential, Size = 1)]
		public struct Fan
		{
			public const uint Performance = 1u;

			public const uint Standard = 2u;

			public const uint Quiet = 3u;

			public const uint Benchmark = 4u;
		}

		[StructLayout(LayoutKind.Sequential, Size = 1)]
		public struct Cpu
		{
			public const uint P1 = 1u;

			public const uint P2 = 2u;

			public const uint P3 = 3u;

			public const uint Benchmark = 4u;
		}

		[StructLayout(LayoutKind.Sequential, Size = 1)]
		public struct DGpu
		{
			public const uint G1 = 1u;

			public const uint G2 = 2u;

			public const uint G3 = 3u;

			public const uint Benchmark = 4u;
		}

		[StructLayout(LayoutKind.Sequential, Size = 1)]
		public struct SysPowerModeIndex
		{
			public const uint Performance = 1u;

			public const uint Balanced = 2u;

			public const uint BatterySaver = 3u;

			public const uint Benchmark = 4u;
		}
	}
	public class DefaultProfileInfo
	{
		public uint P;

		public uint F;

		public uint G;

		public uint P_DC;

		public uint F_DC;

		public uint G_DC;

		public unsafe DefaultProfileInfo()
		{
			//IL_0000: Unknown result type (might be due to invalid IL or missing references)
			//IL_0002: Expected native int or pointer, but got O
			checked
			{
				_ = /*Error near IL_0001: Stack underflow*/+ /*Error near IL_0001: Stack underflow*/;
			}
			_ = *(ushort*)(IntPtr)null;
			/*Error near IL_0003: Unknown opcode: 0xE6*/;
		}
	}
	public class DisplayModeParams
	{
		public string sBrightness;

		public string sRed;

		public string sGreen;

		public string sBlue;

		public string sColorTemp;

		public string sContrast;
	}
	public class DefaultDisplayModeParams
	{
		[StructLayout(LayoutKind.Sequential, Size = 1)]
		public struct Basic
		{
			public const int Brightness = 90;

			public const int Contrast = 0;

			public const int ColorTemp = 0;

			public const int Red = 0;

			public const int Green = 0;

			public const int Blue = 0;
		}

		[StructLayout(LayoutKind.Sequential, Size = 1)]
		public struct Intel
		{
			public const int Brightness = 90;

			public const int Contrast = 50;

			public const int ColorTemp = 4200;

			public const int Red = 128;

			public const int Green = 128;

			public const int Blue = 128;
		}
	}
	public class ServCMD
	{
		[StructLayout(LayoutKind.Sequential, Size = 1)]
		public struct FAN
		{
			public const string GETSTATUS = "GETSTATUS";

			public const string DEFAULT = "DEFAULT";

			public const string FAN_GAMING_MODE = "FAN_GAMING_MODE";

			public const string FAN_GAMING_MODE_BOOST_ON = "FAN_GAMING_MODE_BOOST_ON";

			public const string FAN_GAMING_MODE_BOOST_OFF = "FAN_GAMING_MODE_BOOST_OFF";

			public const string FAN_TURBO_MODE_BOOST_ON = "FAN_TURBO_MODE_BOOST_ON";

			public const string FAN_TURBO_MODE_BOOST_OFF = "FAN_TURBO_MODE_BOOST_OFF";

			public const string FAN_TURBO_MODE = "FAN_TURBO_MODE";

			public const string FAN_OFFICE_MODE = "FAN_OFFICE_MODE";

			public const string FAN_OFFICE_MODE_BASIC = "FAN_OFFICE_MODE_BASIC";

			public const string FAN_OFFICE_MODE_ADVANCED = "FAN_OFFICE_MODE_ADVANCED";

			public const string FAN_OFFICE_MODE_BASIC_L0 = "FAN_OFFICE_MODE_BASIC_L0";

			public const string FAN_OFFICE_MODE_BASIC_L1 = "FAN_OFFICE_MODE_BASIC_L1";

			public const string FAN_OFFICE_MODE_BASIC_L2 = "FAN_OFFICE_MODE_BASIC_L2";

			public const string FAN_OFFICE_MODE_BASIC_L3 = "FAN_OFFICE_MODE_BASIC_L3";

			public const string FAN_OFFICE_MODE_BASIC_L4 = "FAN_OFFICE_MODE_BASIC_L4";

			public const string FAN_OFFICE_MODE_BASIC_L5 = "FAN_OFFICE_MODE_BASIC_L5";

			public const string FAN_OFFICE_MODE_ADVANCED_T1_PWM = "FAN_OFFICE_MODE_ADVANCED_T1_PWM";

			public const string FAN_OFFICE_MODE_ADVANCED_T2_PWM = "FAN_OFFICE_MODE_ADVANCED_T2_PWM";

			public const string FAN_OFFICE_MODE_ADVANCED_T3_PWM = "FAN_OFFICE_MODE_ADVANCED_T3_PWM";

			public const string FAN_OFFICE_MODE_ADVANCED_T4_PWM = "FAN_OFFICE_MODE_ADVANCED_T4_PWM";

			public const string FAN_OFFICE_MODE_ADVANCED_T5_PWM = "FAN_OFFICE_MODE_ADVANCED_T5_PWM";

			public const string FAN_POWER_SETTING_MODE_STD = "FAN_POWER_SETTING_MODE_STD";

			public const string FAN_POWER_SETTING_MODE_ECO = "FAN_POWER_SETTING_MODE_ECO";

			public const string FAN_TURBO_MODE_LV1 = "FAN_TURBO_MODE_LV1";

			public const string FAN_TURBO_MODE_LV2 = "FAN_TURBO_MODE_LV2";

			public const string FAN_TURBO_MODE_LV3 = "FAN_TURBO_MODE_LV3";

			public const string FAN_TURBO_MODE_LV4 = "FAN_TURBO_MODE_LV4";

			public const string FAN_OFFICE_MODE_ADV_MIN_SPEED = "FAN_OFFICE_MODE_ADV_MIN_SPEED";

			public const string FAN_OFFICE_MODE_ADV_MIN_TEMP = "FAN_OFFICE_MODE_ADV_MIN_TEMP";

			public const string FAN_OFFICE_MODE_ADV_EXTRA_SPEED = "FAN_OFFICE_MODE_ADV_EXTRA_SPEED";

			public const string FAN_OFFICE_MODE_ADV_LV1 = "FAN_OFFICE_MODE_ADV_LV1";

			public const string FAN_OFFICE_MODE_ADV_LV2 = "FAN_OFFICE_MODE_ADV_LV2";

			public const string FAN_OFFICE_MODE_ADV_LV3 = "FAN_OFFICE_MODE_ADV_LV3";

			public const string FAN_OFFICE_MODE_ADV_LV4 = "FAN_OFFICE_MODE_ADV_LV4";

			public const string FAN_OFFICE_MODE_ADV_LV1_PWMS = "FAN_OFFICE_MODE_ADV_LV1_PWMS";

			public const string FAN_OFFICE_MODE_ADV_LV2_PWMS = "FAN_OFFICE_MODE_ADV_LV2_PWMS";

			public const string FAN_OFFICE_MODE_ADV_LV3_PWMS = "FAN_OFFICE_MODE_ADV_LV3_PWMS";

			public const string FAN_OFFICE_MODE_ADV_LV4_PWMS = "FAN_OFFICE_MODE_ADV_LV4_PWMS";

			public const string FAN_OFFICE_MODE_ADV_LV4_DEFAULT = "FAN_OFFICE_MODE_ADV_LV4_DEFAULT";

			public const string FAN_OFFICE_MODE_TESTAI_ON = "FAN_OFFICE_MODE_TESTAI_ON";

			public const string FAN_OFFICE_MODE_TESTAI_OFF = "FAN_OFFICE_MODE_TESTAI_OFF";
		}

		[StructLayout(LayoutKind.Sequential, Size = 1)]
		public struct FAN_INTEL
		{
			public const string GETSTATUS = "GETSTATUS";

			public const string DEFAULT = "DEFAULT";

			public const string SYSPOWER_PERFORMANCE_MODE = "SYSPOWER_PERFORMANCE_MODE";

			public const string SYSPOWER_BALANCED_MODE = "SYSPOWER_BALANCED_MODE";

			public const string SYSPOWER_BATTERYSAVER_MODE = "SYSPOWER_BATTERYSAVER_MODE";

			public const string SYSPOWER_PERFORMANCE_SETTING = "SYSPOWER_PERFORMANCE_SETTING";

			public const string SYSPOWER_BALANCED_SETTING = "SYSPOWER_BALANCED_SETTING";

			public const string SYSPOWER_BATTERYSAVER_SETTING = "SYSPOWER_BATTERYSAVER_SETTING";

			public const string BENCHMARK_ON = "BENCHMARK_ON";

			public const string BENCHMARK_OFF = "BENCHMARK_OFF";

			public const string GET_FAN_SPEED_CURVE_SETTING = "GET_FAN_SPEED_CURVE_SETTING";

			public const string SET_FAN_SPEED_CURVE_SETTING = "SET_FAN_SPEED_CURVE_SETTING";

			public const string RESTORE_FAN_SPEED_CURVE_SETTING = "RESTORE_FAN_SPEED_CURVE_SETTING";
		}

		[StructLayout(LayoutKind.Sequential, Size = 1)]
		public struct RGBLB
		{
			public const string GETSTATUS = "GETSTATUS";

			public const string DEFAULT = "DEFAULT";

			public const string POWER_ON = "POWER_ON";

			public const string POWER_OFF = "POWER_OFF";

			public const string RL = "RL";

			public const string GL = "GL";

			public const string BL = "BL";

			public const string RL_DC = "RL_DC";

			public const string GL_DC = "GL_DC";

			public const string BL_DC = "BL_DC";

			public const string COLORFUL_ON = "COLORFUL_ON";

			public const string COLORFUL_OFF = "COLORFUL_OFF";

			public const string BREATHINGLIGHT = "BREATHINGLIGHT";
		}

		[StructLayout(LayoutKind.Sequential, Size = 1)]
		public struct RGBLB_INTEL
		{
			public const string GETSTATUS = "GETSTATUS";

			public const string DEFAULT = "DEFAULT";

			public const string POWER_ON = "POWER_ON";

			public const string POWER_OFF = "POWER_OFF";

			public const string RL = "RL";

			public const string GL = "GL";

			public const string BL = "BL";

			public const string RL_DC = "RL_DC";

			public const string GL_DC = "GL_DC";

			public const string BL_DC = "BL_DC";

			public const string COLORFUL_ON = "COLORFUL_ON";

			public const string COLORFUL_OFF = "COLORFUL_OFF";

			public const string BREATHINGLIGHT = "BREATHINGLIGHT";

			public const string COPY_AC_SETTINGS = "COPY_AC_SETTINGS";
		}

		[StructLayout(LayoutKind.Sequential, Size = 1)]
		public struct MySetting
		{
			public const string KEYBOARD_LIGHTBAR_TIMER_ON = "KEYBOARD_LIGHTBAR_TIMER_ON";

			public const string KEYBOARD_LIGHTBAR_TIMER_OFF = "KEYBOARD_LIGHTBAR_TIMER_OFF";

			public const string DISPLAY_POWER_OFF = "DISPLAY_POWER_OFF";

			public const string GETSTATUS = "GETSTATUS";

			public const string DISPLAY_FEATURE_STATUS_OFF = "DISPLAY_FEATURE_STATUS_OFF";

			public const string DISPLAY_FEATURE_STATUS_ON = "DISPLAY_FEATURE_STATUS_ON";

			public const string DISPLAY_STANDARD_MODE = "DISPLAY_STANDARD_MODE";

			public const string DISPLAY_GAMING_MODE = "DISPLAY_GAMING_MODE";

			public const string DISPLAY_VIDEO_MODE = "DISPLAY_VIDEO_MODE";

			public const string DISPLAY_READ_MODE = "DISPLAY_READ_MODE";

			public const string DISPLAY_CUSTOMIZED_MODE = "DISPLAY_CUSTOMIZED_MODE";

			public const string DISPLAY_GAMING_MODE_VALUE = "DISPLAY_GAMING_MODE_VALUE";

			public const string DISPLAY_VIDEO_MODE_VALUE = "DISPLAY_VIDEO_MODE_VALUE";

			public const string DISPLAY_READ_MODE_VALUE = "DISPLAY_READ_MODE_VALUE";

			public const string DISPLAY_CUSTOMIZED_MODE_VALUE = "DISPLAY_CUSTOMIZED_MODE_VALUE";

			public const string DISPLAY_GAMING_MODE_RECOVERY = "DISPLAY_GAMING_MODE_RECOVERY";

			public const string DISPLAY_VIDEO_MODE_RECOVERY = "DISPLAY_VIDEO_MODE_RECOVERY";

			public const string DISPLAY_READ_MODE_RECOVERY = "DISPLAY_READ_MODE_RECOVERY";

			public const string DISPLAY_CUSTOMIZED_MODE_RECOVERY = "DISPLAY_CUSTOMIZED_MODE_RECOVERY";

			public const string OSD_HIDDEN_ON = "OSD_HIDDEN_ON";

			public const string OSD_HIDDEN_OFF = "OSD_HIDDEN_OFF";

			public const string NV_CTRL_PANEL_AUTOSELECT = "NV_CTRL_PANEL_AUTOSELECT";

			public const string NV_CTRL_PANEL_HIGHPERFORMANCE = "NV_CTRL_PANEL_HIGHPERFORMANCE";

			public const string WINKEY_LOCK = "WINKEY_LOCK";

			public const string WINKEY_UNLOCK = "WINKEY_UNLOCK";

			public const string WINKEY_TRIGGER = "WINKEY_TRIGGER";

			public const string LIGHT_BAR_TRIGGER = "LIGHT_BAR_TRIGGER";

			public const string USB_CHARGER_ON = "USB_CHARGER_ON";

			public const string USB_CHARGER_OFF = "USB_CHARGER_OFF";

			public const string WINKEY_STATUS_LOCK = "WINKEY_STATUS_LOCK";

			public const string WINKEY_STATUS_UNLOCK = "WINKEY_STATUS_UNLOCK";

			public const string LIGHTBAR_STATUS_ON = "LIGHTBAR_STATUS_ON";

			public const string LIGHTBAR_STATUS_OFF = "LIGHTBAR_STATUS_OFF";

			public const string CPU_SILENT_MODE_STATUS_ON = "CPU_SILENT_MODE_STATUS_ON";

			public const string CPU_SILENT_MODE_STATUS_OFF = "CPU_SILENT_MODE_STATUS_OFF";

			public const string USB_CHARGER_STATUS_ON = "USB_CHARGER_STATUS_ON";

			public const string USB_CHARGER_STATUS_OFF = "USB_CHARGER_STATUS_OFF";

			public const string POWER_PLAN_GAMING = "POWER_PLAN_GAMING";

			public const string POWER_PLAN_HIPERFORMANCE = "POWER_PLAN_HIPERFORMANCE";

			public const string POWER_PLAN_BALANCED = "POWER_PLAN_BALANCED";

			public const string POWER_PLAN_POWERSAVING = "POWER_PLAN_POWERSAVING";

			public const string POWER_PLAN_DELETE = "POWER_PLAN_DELETE";

			public const string GAMER_ON = "GAMER_ON";

			public const string GAMER_OFF = "GAMER_OFF";

			public const string UNINSTALL_MYSETTING = "UNINSTALL_MYSETTING";

			public const string SINGLE_COLOR_KBBL_STATUS_ON = "SINGLE_COLOR_KBBL_STATUS_ON";

			public const string SINGLE_COLOR_KBBL_STATUS_OFF = "SINGLE_COLOR_KBBL_STATUS_OFF";

			public const string COLOR_CALIBRATION_ON = "COLOR_CALIBRATION_ON";

			public const string COLOR_CALIBRATION_OFF = "COLOR_CALIBRATION_OFF";

			public const string TOUCHPAD_LED_ON = "TOUCHPAD_LED_ON";

			public const string TOUCHPAD_LED_OFF = "TOUCHPAD_LED_OFF";

			public const string FNKEY_LOCK = "FNKEY_LOCK";

			public const string FNKEY_UNLOCK = "FNKEY_UNLOCK";

			public const string NUMPAD_LOCK = "NUMPAD_LOCK";

			public const string NUMPAD_UNLOCK = "NUMPAD_UNLOCK";
		}

		[StructLayout(LayoutKind.Sequential, Size = 1)]
		public struct MyEC
		{
			public const string WRITE = "WRITE";

			public const string READ = "READ";
		}

		[StructLayout(LayoutKind.Sequential, Size = 1)]
		public struct CustomizeInfoCMD
		{
			public const string GETSETUPINFO = "GETSETUPINFO";

			public const string GETSUPPORT = "GETSUPPORT";
		}

		[StructLayout(LayoutKind.Sequential, Size = 1)]
		public struct Tray
		{
			public const string Lang_GET = "GET";

			public const string Lang_SET = "SET";

			public const string EnableTray = "EnableTray";
		}

		[StructLayout(LayoutKind.Sequential, Size = 1)]
		public struct GamingCenter_WPF
		{
			public const string System_OFF = "System_OFF";
		}
	}
}
namespace UWP_Refactor.Helpers
{
	public static class Json
	{
		[StructLayout(LayoutKind.Auto)]
		[CompilerGenerated]
		private struct <ToObjectAsync>d__0<T> : IAsyncStateMachine
		{
			public int <>1__state;

			public AsyncTaskMethodBuilder<T> <>t__builder;

			public string value;

			private TaskAwaiter<T> <>u__1;

			private void MoveNext()
			{
			//Invalid MethodBodyBlock: Invalid method header: 0x2B 0x22
			}

			void IAsyncStateMachine.MoveNext()
			{
				//ILSpy generated this explicit interface implementation from .override directive in MoveNext
				this.MoveNext();
			}

			[DebuggerHidden]
			private void SetStateMachine(IAsyncStateMachine stateMachine)
			{
			//Invalid MethodBodyBlock: Invalid method header: 0xCB 0x51
			}

			void IAsyncStateMachine.SetStateMachine(IAsyncStateMachine stateMachine)
			{
				//ILSpy generated this explicit interface implementation from .override directive in SetStateMachine
				this.SetStateMachine(stateMachine);
			}
		}

		[StructLayout(LayoutKind.Auto)]
		[CompilerGenerated]
		private struct <StringifyAsync>d__1 : IAsyncStateMachine
		{
			public int <>1__state;

			public AsyncTaskMethodBuilder<string> <>t__builder;

			public object value;

			private TaskAwaiter<string> <>u__1;

			private void MoveNext()
			{
			//Invalid MethodBodyBlock: Invalid method header: 0x2B 0x25
			}

			void IAsyncStateMachine.MoveNext()
			{
				//ILSpy generated this explicit interface implementation from .override directive in MoveNext
				this.MoveNext();
			}

			[DebuggerHidden]
			private void SetStateMachine(IAsyncStateMachine stateMachine)
			{
			//Invalid MethodBodyBlock: Invalid method header: 0x6B 0xC3
			}

			void IAsyncStateMachine.SetStateMachine(IAsyncStateMachine stateMachine)
			{
				//ILSpy generated this explicit interface implementation from .override directive in SetStateMachine
				this.SetStateMachine(stateMachine);
			}
		}

		[AsyncStateMachine(typeof(<ToObjectAsync>d__0<>))]
		public static Task<T> ToObjectAsync<T>(string value)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x9F 0xBE
		}

		[AsyncStateMachine(typeof(<StringifyAsync>d__1))]
		public static Task<string> StringifyAsync(object value)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0xCB 0x29
		}
	}
}
internal class ConfusedByAttribute : Attribute
{
	public ConfusedByAttribute(string P_0)
	{
	//Invalid MethodBodyBlock: Invalid method header: 0x23 0x7D
	}
}
