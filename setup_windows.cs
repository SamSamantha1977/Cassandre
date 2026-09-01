using System;
using System.Diagnostics;
using System.IO;
using System.Security.Principal;
using System.Text;
using System.Windows.Forms;

internal static class CassandraSetup
{
    private const string InstallUrl = "https://raw.githubusercontent.com/SamSamantha1977/Cassandre/main/install-windows.ps1";
    private static readonly string LogPath = Path.Combine(Path.GetTempPath(), "Cassandra-Setup.cmtrace.log");

    [STAThread]
    private static int Main(string[] args)
    {
        try
        {
            Log("Demarrage de setup_windows.exe.", 1);
            if (!IsAdministrator())
            {
                Log("Elevation UAC demandee.", 1);
                var self = new ProcessStartInfo
                {
                    FileName = Application.ExecutablePath,
                    UseShellExecute = true,
                    Verb = "runas",
                    Arguments = "--elevated"
                };
                try
                {
                    using (var p = Process.Start(self))
                    {
                        if (p != null) p.WaitForExit();
                        return p == null ? 1 : p.ExitCode;
                    }
                }
                catch (System.ComponentModel.Win32Exception)
                {
                    Log("Elevation UAC annulee par l'utilisateur.", 2);
                    return 1223;
                }
            }

            string command = "& ([scriptblock]::Create((Invoke-RestMethod -UseBasicParsing '" + InstallUrl + "')))";
            string encoded = Convert.ToBase64String(Encoding.Unicode.GetBytes(command));
            var psi = new ProcessStartInfo
            {
                FileName = "powershell.exe",
                Arguments = "-NoProfile -ExecutionPolicy Bypass -EncodedCommand " + encoded,
                UseShellExecute = false,
                CreateNoWindow = true,
                WindowStyle = ProcessWindowStyle.Hidden
            };

            Log("Lancement de l'installateur public Cassandra depuis GitHub.", 1);
            using (var process = Process.Start(psi))
            {
                if (process == null) throw new InvalidOperationException("Impossible de lancer PowerShell.");
                process.WaitForExit();
                Log("Installateur PowerShell termine avec le code " + process.ExitCode + ".", process.ExitCode == 0 ? 1 : 3);
                if (process.ExitCode != 0)
                {
                    MessageBox.Show(
                        "L'installation de Cassandra n'a pas pu se terminer.\r\n\r\nJournal : " + LogPath,
                        "Cassandra",
                        MessageBoxButtons.OK,
                        MessageBoxIcon.Error);
                    return process.ExitCode;
                }
            }

            MessageBox.Show(
                "Cassandra WORKER est installe.",
                "Cassandra",
                MessageBoxButtons.OK,
                MessageBoxIcon.Information);
            Log("Installation terminee avec succes.", 1);
            return 0;
        }
        catch (Exception ex)
        {
            Log("ECHEC setup_windows.exe: " + ex.Message, 3);
            MessageBox.Show(
                "L'installation de Cassandra n'a pas pu se terminer.\r\n\r\n" + ex.Message + "\r\n\r\nJournal : " + LogPath,
                "Cassandra",
                MessageBoxButtons.OK,
                MessageBoxIcon.Error);
            return 1;
        }
    }

    private static bool IsAdministrator()
    {
        using (WindowsIdentity identity = WindowsIdentity.GetCurrent())
        {
            var principal = new WindowsPrincipal(identity);
            return principal.IsInRole(WindowsBuiltInRole.Administrator);
        }
    }

    private static void Log(string message, int type)
    {
        try
        {
            DateTime now = DateTime.Now;
            string safe = (message ?? string.Empty).Replace("]]>", "] ]>");
            string line = "<![LOG[" + safe + "]LOG]!><time=\"" + now.ToString("HH:mm:ss.fff") +
                          "\" date=\"" + now.ToString("MM-dd-yyyy") +
                          "\" component=\"CassandraSetup\" context=\"\" type=\"" + type +
                          "\" thread=\"" + Process.GetCurrentProcess().Id + "\" file=\"\">";
            File.AppendAllText(LogPath, line + Environment.NewLine, Encoding.UTF8);
        }
        catch { }
    }
}
