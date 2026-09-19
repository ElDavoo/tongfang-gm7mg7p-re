using System.CodeDom.Compiler;
using System.ComponentModel;
using System.Diagnostics;
using System.Globalization;
using System.Resources;
using System.Runtime.CompilerServices;

namespace GCUService.Properties;

[GeneratedCode("System.Resources.Tools.StronglyTypedResourceBuilder", "16.0.0.0")]
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
			if (resourceMan == null)
			{
				resourceMan = new ResourceManager("GCUService.Properties.Resources", typeof(Resources).Assembly);
			}
			return resourceMan;
		}
	}

	[EditorBrowsable(EditorBrowsableState.Advanced)]
	internal static CultureInfo Culture
	{
		get
		{
			return resourceCulture;
		}
		set
		{
			resourceCulture = value;
		}
	}

	internal static string InvalidOperation_Disp_Change_BadDualView => ResourceManager.GetString("InvalidOperation_Disp_Change_BadDualView", resourceCulture);

	internal static string InvalidOperation_Disp_Change_BadFlags => ResourceManager.GetString("InvalidOperation_Disp_Change_BadFlags", resourceCulture);

	internal static string InvalidOperation_Disp_Change_BadMode => ResourceManager.GetString("InvalidOperation_Disp_Change_BadMode", resourceCulture);

	internal static string InvalidOperation_Disp_Change_BadParam => ResourceManager.GetString("InvalidOperation_Disp_Change_BadParam", resourceCulture);

	internal static string InvalidOperation_Disp_Change_Failed => ResourceManager.GetString("InvalidOperation_Disp_Change_Failed", resourceCulture);

	internal static string InvalidOperation_Disp_Change_NotUpdated => ResourceManager.GetString("InvalidOperation_Disp_Change_NotUpdated", resourceCulture);

	internal static string InvalidOperation_Disp_Change_Restart => ResourceManager.GetString("InvalidOperation_Disp_Change_Restart", resourceCulture);

	internal static string InvalidOperation_FatalError => ResourceManager.GetString("InvalidOperation_FatalError", resourceCulture);

	internal static string Msg_Disp_Change => ResourceManager.GetString("Msg_Disp_Change", resourceCulture);

	internal static string Msg_Disp_Change_Original => ResourceManager.GetString("Msg_Disp_Change_Original", resourceCulture);

	internal static string Msg_Disp_Change_Reset => ResourceManager.GetString("Msg_Disp_Change_Reset", resourceCulture);

	internal static string Msg_Disp_Change_Rotate => ResourceManager.GetString("Msg_Disp_Change_Rotate", resourceCulture);

	internal static string Msg_Disp_Change_Successful => ResourceManager.GetString("Msg_Disp_Change_Successful", resourceCulture);

	internal Resources()
	{
	}
}
