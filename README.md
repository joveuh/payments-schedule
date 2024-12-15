<h3>Ever wonder what is coming in and out of your account on a daily basis?</h3>
<h3>Get a summary of your finances and print your payments schedule summary today.</h3>

<p><a href="https://github.com/joveuh/payments-schedule">Payment Schedule repo</a></p>
Clone the repo, from terminal issue:
<br><code>python main.py</code><br>

This will print a sample summary with a sample csv.
To print your own summary, you can provide a comma separated CSV file with the following format:

<br><code>operation,frequency,amount,startDate</code><br>
where operation can be <code>in</code> or <code>out</code> as in money being deposited or withdrawn. 
<br>Frequency can be any of the following<code> Y, BY, Q, M, B, W, D </code><br>
as in <code>Yearly, Bi-Yearly, Quarterly, Monthly, Bi-Weekly Weekly, Daily</code>.<br>

You can invoke the main.py script with the CSV file argument and # of days you want to print the payments schedule for.
For example:
<br><code>python main.py mycsvfile.csv 365</code><br>



Here is a sample screenshot of the csvfile and the payments schedule summary.
-----------------------------------------------
-----------------------------------------------
-----------------------------------------------
![Screenshot 2024-12-14 at 11 19 23 PM](https://github.com/user-attachments/assets/a524b2e1-c302-4d8d-80c5-86848c5fdf60)
-----------------------------------------------
-----------------------------------------------
-----------------------------------------------
![Screenshot 2024-12-14 at 11 27 48 PM](https://github.com/user-attachments/assets/8a75a258-d744-44e5-9339-db3a112b83ea)
